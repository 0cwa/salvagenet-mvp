#!/usr/bin/env python3
"""Create a compact redacted acceptance-evidence record."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def artifact_record(raw: str) -> dict[str, str | None]:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise ValueError(f"artifact escapes repository: {raw}")
    if not resolved.is_file():
        raise ValueError(f"artifact does not exist: {raw}")
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return {
        "path": resolved.relative_to(ROOT).as_posix(),
        "sha256": digest,
        "note": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", required=True)
    parser.add_argument(
        "--status",
        required=True,
        choices=("PASS", "FAIL", "BLOCKED-HARDWARE", "DEFERRED"),
    )
    parser.add_argument("--command", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--environment-json", type=Path)
    args = parser.parse_args()

    gate = args.gate.upper()
    if len(gate) != 3 or gate[0] not in "BU" or not gate[1:].isdigit():
        raise SystemExit("--gate must be Bxx or Uxx")

    environment: dict[str, object] = {}
    if args.environment_json:
        loaded = json.loads(args.environment_json.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise SystemExit("--environment-json must contain an object")
        environment = loaded

    try:
        artifacts = [artifact_record(value) for value in args.artifact]
    except ValueError as exc:
        raise SystemExit(str(exc)) from None

    record = {
        "schemaVersion": 1,
        "gateId": gate,
        "status": args.status,
        "recordedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gitCommit": git_commit(),
        "command": args.command,
        "summary": args.summary,
        "environment": environment,
        "artifacts": artifacts,
    }
    output = ROOT / "evidence/gates" / f"{gate}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
