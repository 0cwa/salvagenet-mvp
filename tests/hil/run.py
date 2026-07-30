#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import traceback

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tests.hil.adapters import AdbDevice, CommandRunner, ControllerCli, HeadscaleLab, SetupBlocked
    from tests.hil.config import ConfigError, HilConfig
    from tests.hil.evidence import EvidenceRecorder, redact
    from tests.hil.lease import DeviceLease
    from tests.hil import scenarios
else:
    from .adapters import AdbDevice, CommandRunner, ControllerCli, HeadscaleLab, SetupBlocked
    from .config import ConfigError, HilConfig
    from .evidence import EvidenceRecorder, redact
    from .lease import DeviceLease
    from . import scenarios


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def source_state(root: Path) -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    ).stdout.strip() or "unknown"
    status_result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    status = status_result.stdout.splitlines() if status_result.returncode == 0 else ["git-status-unavailable"]
    return {"commit": commit, "dirty": bool(status), "status": status}


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="salvagenet-hil")
    parser.add_argument("scenario", choices=("doctor", "facts", "smoke", "mvp", "resilience", "all"))
    parser.add_argument("--config", help="default: .local/hil.json or SALVAGENET_HIL_CONFIG")
    parser.add_argument("--build", action="store_true", help="run paths.buildCommand before installing")
    parser.add_argument(
        "--mode",
        choices=("diagnostic", "candidate"),
        default="diagnostic",
        help="candidate requires a clean source tree and is eligible for reviewed promotion",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    recorder: EvidenceRecorder | None = None
    device: AdbDevice | None = None
    try:
        config = HilConfig.load(root, args.config)
        state = source_state(root)
        recorder = EvidenceRecorder.create(
            config.evidence_directory,
            args.scenario,
            str(state["commit"]),
            file_sha256(config.apk_path),
            config.device_serial,
            evidence_mode=args.mode,
            source_dirty=bool(state["dirty"]),
        )
        recorder.write_json("source-state.json", state)
        lease_metadata = {
            "scenario": args.scenario,
            "evidenceMode": args.mode,
            "sourceCommit": state["commit"],
            "taskId": os.environ.get("AGENT_TASK_ID", "unassigned"),
            "runDirectory": str(recorder.directory.relative_to(root)),
        }
        with DeviceLease(root, config.device_serial, lease_metadata):
            config.require_scenario_authorization(args.scenario)
            if args.mode == "candidate" and state["dirty"]:
                raise ConfigError("candidate HIL runs require a clean source tree")
            runner = CommandRunner(root, recorder)
            device = AdbDevice(config, runner)
            controller = ControllerCli(config, runner)
            mesh = HeadscaleLab(config, runner)

            if args.build:
                runner.run(config.build_command, timeout=3600)
                recorder.apk_sha256 = file_sha256(config.apk_path)
                post_build_state = source_state(root)
                recorder.write_json("source-state-after-build.json", post_build_state)
                recorder.source_dirty = bool(post_build_state["dirty"])
                if post_build_state["commit"] != state["commit"]:
                    raise ConfigError("source commit changed during HIL build")
                if args.mode == "candidate" and post_build_state["dirty"]:
                    raise ConfigError("candidate HIL build changed tracked source state")

            if args.scenario == "doctor":
                scenarios.doctor(config, device, recorder)
            elif args.scenario == "facts":
                recorder.write_json("device-facts.json", device.doctor())
            elif args.scenario == "smoke":
                scenarios.doctor(config, device, recorder)
                scenarios.smoke(config, device, controller, recorder)
            elif args.scenario == "mvp":
                scenarios.doctor(config, device, recorder)
                device.install_apk(config.apk_path)
                device.start_supervisor()
                scenarios.mvp(config, controller, mesh, recorder)
            elif args.scenario == "resilience":
                scenarios.doctor(config, device, recorder)
                device.install_apk(config.apk_path)
                device.start_supervisor()
                if device.count_qemu_processes() != 1:
                    scenarios.smoke(config, device, controller, recorder)
                scenarios.resilience(config, device, controller, recorder)
            elif args.scenario == "all":
                scenarios.doctor(config, device, recorder)
                scenarios.smoke(config, device, controller, recorder)
                scenarios.mvp(config, controller, mesh, recorder)
                scenarios.resilience(config, device, controller, recorder)
            else:
                raise AssertionError(args.scenario)

        path = recorder.finish("PASS")
        print(f"PASS-{args.scenario.upper()}: {path}")
        return 0
    except (SetupBlocked, ConfigError) as exc:
        detail = redact(str(exc), recorder.private_values if recorder else ())
        if recorder:
            recorder.finish("BLOCKED-HARDWARE", detail=detail)
            print(f"evidence: {recorder.directory}", file=sys.stderr)
        print(f"BLOCKED-HARDWARE/SETUP: {detail}", file=sys.stderr)
        return 77
    except (AssertionError, OSError, RuntimeError, TimeoutError) as exc:
        detail = redact(str(exc), recorder.private_values if recorder else ())
        if recorder:
            if device:
                try:
                    (recorder.directory / "logcat.txt").write_text(
                        recorder.bounded(device.logcat(), limit=1024 * 1024), encoding="utf-8"
                    )
                except Exception:
                    pass
            recorder.finish("FAIL", detail=detail)
            print(f"evidence: {recorder.directory}", file=sys.stderr)
        print(f"FAIL-{args.scenario.upper()}: {detail}", file=sys.stderr)
        if os.environ.get("SALVAGENET_HIL_TRACEBACK", "").lower() in {"1", "true", "yes"}:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
