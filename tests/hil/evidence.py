from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


_SECRET_PATTERNS = [
    re.compile(r"(?i)(auth(?:orization)?[-_ ]?key|capability|token|secret|password)([\"' :=]+)([^\s\"']+)"),
    re.compile(r"(?i)(bearer)(\s+)([^\s]+)"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact(value: str) -> str:
    result = value
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}<redacted>", result)
    return result


def bounded(value: str, limit: int = 8192) -> str:
    value = redact(value)
    if len(value) <= limit:
        return value
    return f"<truncated {len(value) - limit} chars>\n{value[-limit:]}"


@dataclass
class EvidenceRecorder:
    directory: Path
    scenario: str
    source_commit: str
    apk_sha256: str | None
    device_serial: str
    started_at: str = field(default_factory=utc_now)
    assertions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        base: Path,
        scenario: str,
        source_commit: str,
        apk_sha256: str | None,
        device_serial: str,
    ) -> "EvidenceRecorder":
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = hashlib.sha256(f"{stamp}:{scenario}:{device_serial}".encode()).hexdigest()[:8]
        directory = base / f"{stamp}-{scenario}-{suffix}"
        directory.mkdir(parents=True, exist_ok=False)
        return cls(directory, scenario, source_commit, apk_sha256, device_serial)

    def record_command(
        self,
        argv: list[str],
        returncode: int,
        duration_seconds: float,
        stdout: str,
        stderr: str,
    ) -> None:
        entry = {
            "at": utc_now(),
            "argv": [redact(item) for item in argv],
            "returnCode": returncode,
            "durationSeconds": round(duration_seconds, 3),
            "stdout": bounded(stdout),
            "stderr": bounded(stderr),
        }
        with (self.directory / "commands.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def assert_that(self, assertion_id: str, passed: bool, detail: str) -> None:
        self.assertions.append(
            {"id": assertion_id, "passed": bool(passed), "detail": redact(detail), "at": utc_now()}
        )
        if not passed:
            raise AssertionError(f"{assertion_id}: {detail}")

    def write_json(self, name: str, value: Any) -> Path:
        path = self.directory / name
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def finish(self, result: str, *, detail: str | None = None) -> Path:
        payload = {
            "schemaVersion": 1,
            "scenario": self.scenario,
            "result": result,
            "detail": redact(detail or ""),
            "sourceCommit": self.source_commit,
            "apkSha256": self.apk_sha256,
            "deviceSerialHash": hashlib.sha256(self.device_serial.encode()).hexdigest(),
            "startedAt": self.started_at,
            "finishedAt": utc_now(),
            "assertions": self.assertions,
        }
        return self.write_json("run.json", payload)
