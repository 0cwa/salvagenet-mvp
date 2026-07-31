#!/usr/bin/env python3
"""Bounded forbidden-material scan for H02A seed inputs and guest state."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Iterable

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[3] if len(SCRIPT_PATH.parents) > 3 else Path.cwd()
PATTERNS = (
    ("tailscale-key", re.compile(rb"tskey-(?:auth|client)-[A-Za-z0-9_-]{12,}")),
    ("headscale-key", re.compile(rb"hskey-[A-Za-z0-9_-]{12,}")),
    ("bootstrap-token", re.compile(rb"(?:NODEHOST_)?BOOTSTRAP_TOKEN=[A-Za-z0-9_-]{16,}")),
    ("metadata-base", re.compile(rb"NODEHOST_METADATA_BASE=https?://[^\x00\s]{4,}")),
    ("callback-capability", re.compile(rb"(?:NODEHOST_)?CALLBACK_CAPABILITY=[A-Za-z0-9._-]{16,}")),
)
MAX_JSON_BYTES = 256 * 1024
MAX_FILES = 512
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_PROCESS_ENVIRON = 512


class ScanError(RuntimeError):
    pass


def finding(path: str, category: str) -> dict[str, str]:
    return {"path": path[:512], "category": category}


def pattern_findings(data: bytes, label: str) -> list[dict[str, str]]:
    return [finding(label, category) for category, pattern in PATTERNS if pattern.search(data)]


def scan_regular_files(paths: Iterable[Path]) -> tuple[list[dict[str, str]], int, int]:
    findings: list[dict[str, str]] = []
    files = 0
    total = 0
    for path in paths:
        if files >= MAX_FILES:
            findings.append(finding(str(path), "file-count-bound-exceeded"))
            break
        try:
            if path.is_symlink() or not path.is_file():
                continue
            size = path.stat().st_size
            if size > MAX_FILE_BYTES:
                findings.append(finding(str(path), "file-byte-bound-exceeded"))
                continue
            if total + size > MAX_TOTAL_BYTES:
                findings.append(finding(str(path), "total-byte-bound-exceeded"))
                break
            data = path.read_bytes()
        except OSError:
            continue
        files += 1
        total += len(data)
        findings.extend(pattern_findings(data, str(path)))
    return findings, files, total


def walk_roots(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_symlink() or not root.exists():
            continue
        if root.is_file():
            yield root
            continue
        for directory, names, filenames in os.walk(root, followlinks=False):
            names[:] = sorted(name for name in names if not (Path(directory) / name).is_symlink())
            for name in sorted(filenames):
                yield Path(directory) / name


def remote_scan() -> dict[str, Any]:
    roots = [
        Path("/var/lib/cloud"),
        Path("/var/log/cloud-init.log"),
        Path("/var/log/cloud-init-output.log"),
        Path("/run"),
        Path("/tmp"),
    ]
    findings, file_count, total_bytes = scan_regular_files(walk_roots(roots))
    if Path("/var/lib/nodehost/bootstrap.env").exists():
        findings.append(finding("/var/lib/nodehost/bootstrap.env", "bootstrap-environment-present"))
    if shutil.which("tailscale") is not None:
        findings.append(finding("PATH", "mesh-client-installed"))
    for path in (Path("/var/lib/tailscale/tailscaled.state"), Path("/var/lib/tailscale")):
        if path.exists():
            findings.append(finding(str(path), "mesh-state-present"))
    process_count = 0
    for process in sorted(Path("/proc").glob("[0-9]*"), key=lambda value: value.name):
        if process_count >= MAX_PROCESS_ENVIRON:
            findings.append(finding("/proc/*/environ", "process-count-bound-exceeded"))
            break
        environ = process / "environ"
        comm = process / "comm"
        try:
            if comm.is_file() and comm.read_text(encoding="utf-8", errors="replace").strip() == "tailscaled":
                findings.append(finding(str(comm), "mesh-process-running"))
            if environ.is_file() and not environ.is_symlink():
                data = environ.read_bytes()
                if len(data) > MAX_FILE_BYTES:
                    findings.append(finding(str(environ), "process-environment-bound-exceeded"))
                else:
                    findings.extend(pattern_findings(data, str(environ)))
        except OSError:
            pass
        process_count += 1
    return {
        "passed": not findings,
        "findings": findings,
        "scannedPaths": [str(path) for path in roots] + ["/proc/*/environ", "/proc/*/comm"],
        "stats": {"files": file_count, "bytes": total_bytes, "processes": process_count},
    }


def validate_state_directory(state: Path) -> Path:
    local_root = (ROOT / ".local").resolve(strict=True)
    candidate = state.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if candidate.is_symlink():
        raise ScanError("H02A state directory must not be a symlink")
    resolved = candidate.resolve(strict=True)
    try:
        relative = resolved.relative_to(local_root)
    except ValueError as exc:
        raise ScanError(f"H02A state directory must remain under {local_root}") from exc
    if not relative.parts:
        raise ScanError("H02A state directory cannot be the repository .local root")
    return resolved


def read_remote(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size not in range(1, MAX_JSON_BYTES + 1):
        raise ScanError("remote scan result is missing, oversized, or unsafe")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScanError(f"cannot read remote scan result: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"findings", "passed", "scannedPaths", "stats"}:
        raise ScanError("remote scan result has an invalid schema")
    if not isinstance(value["findings"], list) or not isinstance(value["scannedPaths"], list):
        raise ScanError("remote scan result has invalid collections")
    return value


def atomic_json(path: Path, value: Any) -> None:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_JSON_BYTES:
        raise ScanError("combined scan result exceeds the byte bound")
    if path.is_symlink():
        raise ScanError("combined scan path must not be a symlink")
    temporary = path.with_name(path.name + ".tmp")
    if temporary.is_symlink():
        raise ScanError("combined scan temporary path must not be a symlink")
    temporary.write_bytes(encoded)
    temporary.chmod(0o600)
    temporary.replace(path)


def combine_scan(state_path: Path, stage: str, remote_path: Path) -> dict[str, Any]:
    if stage not in {"initial", "guest-reboot", "qemu-restart"}:
        raise ScanError("invalid H02A scan stage")
    state = validate_state_directory(state_path)
    remote = read_remote(remote_path)
    local_paths = [state / "vendor-data", state / "user-data", state / "meta-data"]
    local_findings, _, _ = scan_regular_files(local_paths)
    findings = list(remote["findings"]) + local_findings
    scanned = list(remote["scannedPaths"]) + [str(path) for path in local_paths]
    result = {
        "passed": not findings,
        "findings": findings,
        "scannedPaths": scanned,
    }
    atomic_json(state / f"secret-scan-{stage}.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("remote")
    combine = sub.add_parser("combine")
    combine.add_argument("--state", type=Path, required=True)
    combine.add_argument("--stage", required=True)
    combine.add_argument("--remote", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "remote":
            print(json.dumps(remote_scan(), indent=2, sort_keys=True))
        else:
            result = combine_scan(args.state, args.stage, args.remote)
            print(json.dumps(result, indent=2, sort_keys=True))
            if not result["passed"]:
                return 1
        return 0
    except (OSError, ScanError, json.JSONDecodeError) as exc:
        print(f"H02A scan error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
