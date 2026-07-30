#!/usr/bin/env python3
"""Validate and promote one reviewed HIL run into a compact gate record."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GATE_REQUIREMENTS: dict[str, tuple[str, set[str]]] = {
    "B02": ("smoke", {"smoke.profile-present", "smoke.one-qemu", "smoke.graceful-stop", "smoke.restart-one-qemu"}),
    "B07": ("resilience", {"resilience.service-restart", "resilience.qemu-restart"}),
    "B08": ("mvp", {"mvp.host-mesh"}),
    "B09": ("mvp", {"mvp.host-api"}),
    "B10": ("mvp", {"mvp.vm-apply"}),
    "B12": ("mvp", {"mvp.guest-ssh"}),
    "B13": ("mvp", {"mvp.guest-mesh-disabled", "mvp.recovery-ssh"}),
    "B16": ("resilience", {"resilience.reboot"}),
    "B17": ("resilience", {"resilience.controller-unavailable"}),
}


def current_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def load_run(run_directory: Path) -> dict[str, Any]:
    resolved = run_directory.resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise ValueError("run directory must be inside the repository")
    path = resolved / "run.json"
    if not path.is_file():
        raise ValueError(f"missing HIL run record: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("run.json must contain an object")
    return value


def validate_run(gate: str, run: dict[str, Any], commit: str) -> set[str]:
    gate = gate.upper()
    if gate not in GATE_REQUIREMENTS:
        raise ValueError(f"automatic HIL promotion is not defined for {gate}")
    scenario, required = GATE_REQUIREMENTS[gate]
    if run.get("result") != "PASS":
        raise ValueError("only a PASS HIL run can be promoted")
    if run.get("evidenceMode") != "candidate" or run.get("sourceDirty") is not False:
        raise ValueError("only a clean candidate HIL run can be promoted")
    if run.get("promotable") is not True:
        raise ValueError("HIL run is explicitly non-promotable")
    if run.get("scenario") not in {scenario, "all"}:
        raise ValueError(f"{gate} requires scenario {scenario} or all")
    if run.get("sourceCommit") != commit:
        raise ValueError("HIL sourceCommit does not match current HEAD")
    if not isinstance(run.get("apkSha256"), str) or not SHA256.fullmatch(run["apkSha256"]):
        raise ValueError("HIL run is not bound to a valid APK SHA-256")
    assertions = {
        item.get("id"): item
        for item in run.get("assertions", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = sorted(
        assertion_id
        for assertion_id in required
        if assertion_id not in assertions
        or assertions[assertion_id].get("passed") is not True
        or assertions[assertion_id].get("skipped") is True
    )
    if missing:
        raise ValueError(f"required HIL assertions are missing/not passed: {missing}")
    return required


def relative(path: Path) -> str:
    resolved = path.resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise ValueError(f"artifact escapes repository: {path}")
    return resolved.relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--command")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    gate = args.gate.upper()
    try:
        run = load_run(args.run_dir)
        required = validate_run(gate, run, current_commit())
        run_directory = args.run_dir.resolve()
        artifacts = [run_directory / "run.json"]
        for name in (
            "source-state.json", "device-facts.json", "commands.jsonl", "capabilities.json",
            "profiles.json", "images.json", "desired-vm.json", "vms-before.json", "vms-after.json",
            "artifact-set.json",
        ):
            path = run_directory / name
            if path.is_file():
                artifacts.append(path)
        environment = {
            "scenario": str(run.get("scenario")),
            "evidenceMode": str(run.get("evidenceMode")),
            "apkSha256": str(run.get("apkSha256")),
            "deviceSerialHash": str(run.get("deviceSerialHash")),
            "requiredAssertions": ",".join(sorted(required)),
        }
        environment_path = run_directory / "promotion-environment.json"
        command = args.command or f"python3 tests/hil/run.py {run.get('scenario')} --mode candidate"
        preview = {
            "gate": gate,
            "summary": args.summary,
            "command": command,
            "artifacts": [relative(path) for path in artifacts],
            "environment": environment,
        }
        if not args.write:
            print(json.dumps(preview, indent=2))
            print("dry-run: review the HIL directory and pass --write to promote")
            return 0
        environment_path.write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
        argv = [
            sys.executable,
            str(ROOT / "tools/evidence/record.py"),
            "--gate", gate,
            "--status", "PASS",
            "--command", command,
            "--summary", args.summary,
            "--environment-json", str(environment_path),
        ]
        for artifact in [*artifacts, environment_path]:
            argv.extend(["--artifact", relative(artifact)])
        subprocess.run(argv, cwd=ROOT, check=True)
        subprocess.run([sys.executable, "tools/ci/check-evidence.py"], cwd=ROOT, check=True)
        return 0
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    raise SystemExit(main())
