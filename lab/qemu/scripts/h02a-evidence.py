#!/usr/bin/env python3
"""Create and finalize bounded H02A host-QEMU evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BOOT_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SECRET = re.compile(
    r"(?:tskey-(?:auth|client)-[A-Za-z0-9_-]{12,}|hskey-[A-Za-z0-9_-]{12,}|"
    r"(?i:bootstrap[_-]?token)[=:][A-Za-z0-9._-]{8,}|"
    r"(?i:callback[_-]?capability)[=:][A-Za-z0-9._-]{8,})"
)
MAX_REQUIRED_TEXT_BYTES = 64 * 1024
MAX_LOG_TAIL_BYTES = 16 * 1024
MAX_EVIDENCE_BYTES = 512 * 1024
STAGES = ("initial", "guest-reboot", "qemu-restart")
BASE_IMAGE = "ubuntu-24.04-server-cloudimg-arm64.img"


class EvidenceError(RuntimeError):
    pass


def validate_state_directory(state: Path) -> Path:
    local_root = (ROOT / ".local").resolve(strict=True)
    candidate = state.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if candidate.is_symlink():
        raise EvidenceError("H02A state directory must not be a symlink")
    resolved = candidate.resolve(strict=True)
    try:
        relative = resolved.relative_to(local_root)
    except ValueError as exc:
        raise EvidenceError(f"H02A state directory must remain under {local_root}") from exc
    if not relative.parts:
        raise EvidenceError("H02A state directory cannot be the repository .local root")
    return resolved


def read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file() or path.stat().st_size not in range(1, MAX_EVIDENCE_BYTES + 1):
        raise EvidenceError(f"required bounded JSON is missing or unsafe: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read {path}: {exc}") from exc


def atomic_json(path: Path, value: Any) -> None:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if not encoded or len(encoded) > MAX_EVIDENCE_BYTES:
        raise EvidenceError("evidence exceeds the byte bound")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise EvidenceError("evidence path must not be a symlink")
    temporary = path.with_name(path.name + ".tmp")
    if temporary.is_symlink():
        raise EvidenceError("temporary evidence path must not be a symlink")
    temporary.write_bytes(encoded)
    temporary.chmod(0o600)
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def bounded_text(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"log path is missing or unsafe: {path}")
    digest = hashlib.sha256()
    tail = bytearray()
    total = 0
    with path.open("rb") as handle:
        while chunk := handle.read(8192):
            total += len(chunk)
            digest.update(chunk)
            tail.extend(chunk)
            if len(tail) > MAX_LOG_TAIL_BYTES:
                del tail[: len(tail) - MAX_LOG_TAIL_BYTES]
    text = bytes(tail).decode("utf-8", "replace")
    text = SECRET.sub("[REDACTED]", text)
    return {
        "sha256": digest.hexdigest(),
        "sizeBytes": total,
        "truncatedToTail": total > MAX_LOG_TAIL_BYTES,
        "tail": text,
    }


def required_text(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size not in range(1, MAX_REQUIRED_TEXT_BYTES + 1):
        raise EvidenceError(f"required bounded text is missing or unsafe: {path}")
    return path.read_text(encoding="utf-8").strip()


def require_exact_boolean_map(value: Any, expected: dict[str, bool], label: str) -> dict[str, bool]:
    if value != expected:
        raise EvidenceError(f"{label} result differs from the closed contract")
    return expected


def stage_result(state: Path, stage: str) -> dict[str, Any]:
    qmp = read_json(state / f"qmp-{stage}.json")
    scan = read_json(state / f"secret-scan-{stage}.json")
    auth = read_json(state / f"ssh-auth-{stage}.json")
    cloud_init = required_text(state / f"cloud-init-{stage}.txt")
    sshd = required_text(state / f"sshd-{stage}.txt")
    readiness = required_text(state / f"readiness-{stage}.txt")
    boot_id = required_text(state / f"boot-id-{stage}.txt")
    if not BOOT_ID.fullmatch(boot_id):
        raise EvidenceError(f"invalid boot ID for stage {stage}")
    if qmp != {"running": True, "status": "running"}:
        raise EvidenceError(f"stage {stage} lacks QMP running evidence")
    if readiness != "h02a-ready":
        raise EvidenceError(f"stage {stage} lacks the readiness marker")
    if not isinstance(scan, dict) or set(scan) != {"findings", "passed", "scannedPaths"}:
        raise EvidenceError(f"stage {stage} secret scan schema is invalid")
    if scan["passed"] is not True or scan["findings"] != []:
        raise EvidenceError(f"stage {stage} secret scan did not pass")
    if not isinstance(scan["scannedPaths"], list) or not scan["scannedPaths"]:
        raise EvidenceError(f"stage {stage} secret scan has no bounded scope")
    expected_auth = {
        "keyOnlyLoopbackSsh": True,
        "rootKeyLoginRejected": True,
        "passwordAuthenticationDisabled": True,
        "keyboardInteractiveDisabled": True,
        "rootLoginDisabled": True,
    }
    require_exact_boolean_map(auth, expected_auth, f"stage {stage} SSH authentication")
    expected_sshd = {
        "passwordauthentication no",
        "kbdinteractiveauthentication no",
        "permitrootlogin no",
    }
    observed_sshd = {line.strip().lower() for line in sshd.splitlines() if line.strip()}
    if observed_sshd != expected_sshd:
        raise EvidenceError(f"stage {stage} SSH policy differs from the closed contract")
    if "status: done" not in cloud_init.lower():
        raise EvidenceError(f"stage {stage} cloud-init is not done")
    return {
        "qmp": qmp,
        "bootId": boot_id,
        "cloudInitStatus": "done",
        "readiness": readiness,
        "sshPolicy": sorted(expected_sshd),
        "sshAuthentication": auth,
        "secretScan": scan,
    }


def validate_preflight(preflight: Any) -> dict[str, Any]:
    if not isinstance(preflight, dict) or preflight.get("evidenceClass") != "host-qemu-preflight":
        raise EvidenceError("preflight evidence is invalid")
    for field in ("androidHardwareValidated", "physicalGateEligible", "guestMeshValidated"):
        if preflight.get(field) is not False:
            raise EvidenceError(f"preflight classification is invalid: {field}")
    source = preflight.get("source")
    if not isinstance(source, dict) or not COMMIT.fullmatch(source.get("commit", "")):
        raise EvidenceError("preflight has no exact source commit")
    if source.get("dirtyTracked") is not False:
        raise EvidenceError("reviewable H02A evidence requires a clean tracked worktree")
    image = preflight.get("image")
    if not isinstance(image, dict) or not re.fullmatch(r"[0-9a-f]{64}", image.get("sha256", "")):
        raise EvidenceError("preflight has no exact image identity")
    if not isinstance(image.get("sizeBytes"), int) or image["sizeBytes"] <= 0:
        raise EvidenceError("preflight image size is invalid")
    return preflight


def create_evidence(state_path: Path) -> Path:
    state = validate_state_directory(state_path)
    preflight = validate_preflight(read_json(state / "preflight.json"))
    stages = {stage: stage_result(state, stage) for stage in STAGES}
    boot_ids = [stages[stage]["bootId"] for stage in STAGES]
    if len(set(boot_ids)) != len(boot_ids):
        raise EvidenceError("guest reboot and QEMU restart did not produce distinct boot IDs")
    source = preflight["source"]
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + source["commit"][:12]
    directory = state / "evidence" / run_id
    if directory.exists() or directory.is_symlink():
        raise EvidenceError("evidence run directory already exists or is unsafe")
    directory.mkdir(mode=0o700, parents=True)

    logs: dict[str, Any] = {}
    for stage in STAGES:
        for name in ("serial", "qemu.stderr", "qemu.stdout"):
            path = state / f"{name}-{stage}.log"
            if path.is_file() and not path.is_symlink():
                logs[f"{stage}:{name}"] = bounded_text(path)

    evidence = {
        "schemaVersion": 1,
        "evidenceClass": "host-qemu",
        "generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "androidHardwareValidated": False,
        "physicalGateEligible": False,
        "guestMeshValidated": False,
        "preflight": preflight,
        "stages": stages,
        "restartChecks": {
            "guestRebootChangedBootId": boot_ids[0] != boot_ids[1],
            "qemuStopStartChangedBootId": boot_ids[1] != boot_ids[2],
        },
        "logs": logs,
        "cleanup": {"completed": False},
    }
    path = directory / "evidence.json"
    atomic_json(path, evidence)
    return path


def finalize_cleanup(state_path: Path, evidence_path: Path) -> None:
    state = validate_state_directory(state_path)
    evidence_path = evidence_path.resolve(strict=True)
    try:
        evidence_path.relative_to((state / "evidence").resolve(strict=True))
    except ValueError as exc:
        raise EvidenceError("evidence path is outside the H02A evidence directory") from exc
    if evidence_path.is_symlink() or evidence_path.name != "evidence.json":
        raise EvidenceError("evidence path is unsafe")
    evidence = read_json(evidence_path)
    preflight = validate_preflight(evidence.get("preflight"))
    retained_names = sorted(path.name for path in state.iterdir())
    expected = sorted([BASE_IMAGE, "evidence"])
    if retained_names != expected:
        raise EvidenceError(f"cleanup retained unexpected state: {retained_names}")
    base = state / BASE_IMAGE
    evidence_root = state / "evidence"
    if base.is_symlink() or evidence_root.is_symlink() or not base.is_file() or not evidence_root.is_dir():
        raise EvidenceError("cleanup retained unsafe cache or evidence")
    image = preflight["image"]
    if base.stat().st_size != image["sizeBytes"] or sha256_file(base) != image["sha256"]:
        raise EvidenceError("retained image cache differs from preflight")
    receipt = read_json(evidence_path.parent / "cleanup.json")
    if not isinstance(receipt, dict) or receipt.get("schemaVersion") != 1:
        raise EvidenceError("cleanup receipt is invalid")
    if receipt.get("qemuStopped") is not True or receipt.get("retained") != expected:
        raise EvidenceError("cleanup receipt does not prove quiescence and retention")
    removed = receipt.get("removed")
    if not isinstance(removed, list) or not removed or any(not isinstance(item, str) for item in removed):
        raise EvidenceError("cleanup receipt has no removed-file inventory")
    evidence["cleanup"] = {
        "completed": True,
        "retained": expected,
        "removed": sorted(set(removed)),
        "baseImageSha256": image["sha256"],
        "receiptSha256": sha256_file(evidence_path.parent / "cleanup.json"),
    }
    atomic_json(evidence_path, evidence)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--state", type=Path, required=True)
    finalize = sub.add_parser("finalize-cleanup")
    finalize.add_argument("--state", type=Path, required=True)
    finalize.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "create":
            print(create_evidence(args.state))
        else:
            finalize_cleanup(args.state, args.evidence)
        return 0
    except (EvidenceError, OSError, json.JSONDecodeError) as exc:
        print(f"H02A evidence error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
