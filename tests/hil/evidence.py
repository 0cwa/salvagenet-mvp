from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


_SECRET_PATTERNS = [
    re.compile(r"(?i)(auth(?:orization)?[-_ ]?key|capability|token|secret|password)([\"' :=]+)([^\s\"']+)"),
    re.compile(r"(?i)(bearer)(\s+)([^\s]+)"),
    re.compile(r"(?i)\btskey-(?:auth|client|api)-[A-Za-z0-9_-]+\b"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact(value: str, private_values: Iterable[str] = ()) -> str:
    result = value
    for private in sorted({item for item in private_values if len(item) >= 4}, key=len, reverse=True):
        result = result.replace(private, "<redacted-private>")
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 3:
            result = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}<redacted>", result)
        else:
            result = pattern.sub("<redacted-tailscale-key>", result)
    return result


def bounded(value: str, limit: int = 8192, private_values: Iterable[str] = ()) -> str:
    value = redact(value, private_values)
    if len(value) <= limit:
        return value
    return f"<truncated {len(value) - limit} chars>\n{value[-limit:]}"


def _redact_json(value: Any, private_values: Iterable[str]) -> Any:
    if isinstance(value, str):
        return redact(value, private_values)
    if isinstance(value, list):
        return [_redact_json(item, private_values) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_json(item, private_values) for key, item in value.items()}
    return value


@dataclass
class EvidenceRecorder:
    directory: Path
    scenario: str
    source_commit: str
    apk_sha256: str | None
    device_serial: str
    started_at: str = field(default_factory=utc_now)
    assertions: list[dict[str, Any]] = field(default_factory=list)
    private_values: tuple[str, ...] = field(default_factory=tuple)

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
        return cls(
            directory,
            scenario,
            source_commit,
            apk_sha256,
            device_serial,
            private_values=(device_serial,),
        )

    def redact(self, value: str) -> str:
        return redact(value, self.private_values)

    def bounded(self, value: str, limit: int = 8192) -> str:
        return bounded(value, limit, self.private_values)

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
            "argv": [self.redact(item) for item in argv],
            "returnCode": returncode,
            "durationSeconds": round(duration_seconds, 3),
            "stdout": self.bounded(stdout),
            "stderr": self.bounded(stderr),
        }
        with (self.directory / "commands.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def assert_that(self, assertion_id: str, passed: bool, detail: str) -> None:
        self.assertions.append(
            {"id": assertion_id, "passed": bool(passed), "detail": self.redact(detail), "at": utc_now()}
        )
        if not passed:
            raise AssertionError(f"{assertion_id}: {detail}")

    def write_json(self, name: str, value: Any) -> Path:
        path = self.directory / name
        safe = _redact_json(value, self.private_values)
        path.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def finish(self, result: str, *, detail: str | None = None) -> Path:
        payload = {
            "schemaVersion": 1,
            "scenario": self.scenario,
            "result": result,
            "detail": self.redact(detail or ""),
            "sourceCommit": self.source_commit,
            "apkSha256": self.apk_sha256,
            "deviceSerialHash": hashlib.sha256(self.device_serial.encode()).hexdigest(),
            "startedAt": self.started_at,
            "finishedAt": utc_now(),
            "assertions": self.assertions,
        }
        return self.write_json("run.json", payload)
