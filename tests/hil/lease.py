from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import TextIO

from .adapters import SetupBlocked


class DeviceLease:
    def __init__(self, root: Path, serial: str, metadata: dict[str, object]):
        serial_hash = hashlib.sha256(serial.encode()).hexdigest()
        self.path = root / ".local" / "hil-locks" / f"{serial_hash}.lock"
        self.metadata = {**metadata, "pid": os.getpid(), "deviceSerialHash": serial_hash}
        self.handle: TextIO | None = None

    def __enter__(self) -> "DeviceLease":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.handle.seek(0)
            holder = self.handle.read().strip() or "unknown holder"
            self.handle.close()
            self.handle = None
            raise SetupBlocked(f"configured device is already leased: {holder}") from exc
        self.handle.seek(0)
        self.handle.truncate()
        json.dump(self.metadata, self.handle, sort_keys=True)
        self.handle.write("\n")
        self.handle.flush()
        os.fsync(self.handle.fileno())
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        if self.handle is None:
            return
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None
