#!/usr/bin/env python3
"""Bounded, closed QMP status client for H02A host-QEMU qualification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import sys
import time
from typing import Any, Callable

MAX_MESSAGE_BYTES = 64 * 1024
POLL_SECONDS = 0.2
ALLOWED_COMMANDS = frozenset({"qmp_capabilities", "query-status"})


class QmpError(RuntimeError):
    pass


class QmpClient:
    def __init__(self, socket_path: Path, timeout_seconds: float = 5.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.socket_path = socket_path
        self.timeout_seconds = timeout_seconds
        self.socket: socket.socket | None = None
        self.buffer = bytearray()
        self.next_id = 1

    def __enter__(self) -> "QmpClient":
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(self.timeout_seconds)
        try:
            connection.connect(str(self.socket_path))
            self.socket = connection
            greeting = self._read_message()
            if not isinstance(greeting.get("QMP"), dict):
                raise QmpError("QMP greeting is invalid")
            self.execute("qmp_capabilities")
            return self
        except BaseException:
            connection.close()
            self.socket = None
            raise

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def _read_message(self) -> dict[str, Any]:
        connection = self.socket
        if connection is None:
            raise QmpError("QMP client is not connected")
        while True:
            newline = self.buffer.find(b"\n")
            if newline >= 0:
                raw = bytes(self.buffer[:newline]).strip()
                del self.buffer[: newline + 1]
                if not raw:
                    continue
                if len(raw) > MAX_MESSAGE_BYTES:
                    raise QmpError("QMP message exceeds the byte bound")
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise QmpError("QMP sent malformed JSON") from exc
                if not isinstance(value, dict):
                    raise QmpError("QMP message is not an object")
                return value
            if len(self.buffer) >= MAX_MESSAGE_BYTES:
                raise QmpError("QMP message exceeds the byte bound")
            chunk = connection.recv(min(8192, MAX_MESSAGE_BYTES - len(self.buffer)))
            if not chunk:
                raise QmpError("QMP closed before a complete response")
            self.buffer.extend(chunk)

    def _receive_until(self, predicate: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise QmpError("QMP response deadline expired")
            connection = self.socket
            if connection is None:
                raise QmpError("QMP client is not connected")
            connection.settimeout(remaining)
            message = self._read_message()
            if predicate(message):
                return message

    def execute(self, command: str) -> Any:
        if command not in ALLOWED_COMMANDS:
            raise QmpError("QMP command is not admitted")
        request_id = self.next_id
        self.next_id += 1
        payload = json.dumps(
            {"execute": command, "id": request_id}, separators=(",", ":")
        ).encode("utf-8") + b"\r\n"
        connection = self.socket
        if connection is None:
            raise QmpError("QMP client is not connected")
        connection.sendall(payload)
        response = self._receive_until(lambda message: message.get("id") == request_id)
        if "error" in response:
            raise QmpError("QMP command returned an error")
        if "return" not in response:
            raise QmpError("QMP response has no return value")
        return response["return"]

    def query_status(self) -> str:
        result = self.execute("query-status")
        if not isinstance(result, dict) or not isinstance(result.get("status"), str):
            raise QmpError("query-status response is invalid")
        status = result["status"]
        if len(status) > 64 or not status:
            raise QmpError("query-status value is out of bounds")
        return status


def wait_for_status(socket_path: Path, timeout_seconds: float, require_running: bool) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    deadline = time.monotonic() + timeout_seconds
    last_error: str | None = None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise QmpError(f"QMP did not become ready: {last_error or 'deadline expired'}")
        try:
            with QmpClient(socket_path, timeout_seconds=min(5.0, remaining)) as client:
                status = client.query_status()
            if not require_running or status == "running":
                return {"status": status, "running": status == "running"}
            last_error = f"status={status}"
        except (OSError, QmpError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        sleep_for = min(POLL_SECONDS, max(deadline - time.monotonic(), 0))
        if sleep_for > 0:
            time.sleep(sleep_for)


def atomic_output(path: Path, encoded: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise QmpError("QMP output path must not traverse a symlink")
    temporary = path.with_name(path.name + ".tmp")
    if temporary.is_symlink():
        raise QmpError("QMP temporary output path must not be a symlink")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--wait", type=float, default=120.0)
    parser.add_argument("--allow-non-running", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = wait_for_status(args.socket, args.wait, not args.allow_non_running)
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output is None:
            sys.stdout.write(encoded)
        else:
            atomic_output(args.output, encoded)
        return 0
    except (OSError, QmpError, ValueError) as exc:
        print(f"H02A QMP error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
