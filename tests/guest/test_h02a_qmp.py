#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "lab/qemu/scripts/h02a-qmp.py"

spec = importlib.util.spec_from_file_location("nodehost_h02a_qmp", HELPER)
assert spec and spec.loader
qmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qmp)


class FakeQmpServer:
    def __init__(self, path: Path, status: str = "running", greeting: object | None = None) -> None:
        self.path = path
        self.status = status
        self.greeting = greeting if greeting is not None else {"QMP": {"version": {"qemu": {"major": 9}}}}
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.failure: BaseException | None = None

    def __enter__(self) -> "FakeQmpServer":
        self.thread.start()
        if not self.ready.wait(2):
            raise RuntimeError("fake QMP server did not start")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.thread.join(2)
        if self.failure is not None:
            raise self.failure

    def run(self) -> None:
        try:
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(self.path))
            listener.listen(1)
            self.ready.set()
            connection, _ = listener.accept()
            with connection, listener:
                stream = connection.makefile("rb")
                connection.sendall(json.dumps(self.greeting).encode() + b"\r\n")
                capabilities_line = stream.readline()
                if not capabilities_line:
                    return
                capabilities = json.loads(capabilities_line)
                connection.sendall(json.dumps({"event": "RESET"}).encode() + b"\r\n")
                connection.sendall(json.dumps({"return": {}, "id": capabilities["id"]}).encode() + b"\r\n")
                query_line = stream.readline()
                if not query_line:
                    return
                query = json.loads(query_line)
                connection.sendall(
                    json.dumps({"return": {"status": self.status}, "id": query["id"]}).encode() + b"\r\n"
                )
        except (BrokenPipeError, ConnectionResetError):
            pass
        except BaseException as failure:
            self.failure = failure
            self.ready.set()


class H02AQmpTests(unittest.TestCase):
    def test_query_status_negotiates_capabilities_and_ignores_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "qmp.sock"
            with FakeQmpServer(path):
                result = qmp.wait_for_status(path, 2, require_running=True)
            self.assertEqual({"status": "running", "running": True}, result)

    def test_non_running_status_is_rejected_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "qmp.sock"
            with FakeQmpServer(path, "paused"):
                with self.assertRaises(qmp.QmpError):
                    qmp.wait_for_status(path, 0.5, require_running=True)

    def test_only_closed_commands_are_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "qmp.sock"
            with FakeQmpServer(path):
                with qmp.QmpClient(path, timeout_seconds=2) as client:
                    with self.assertRaisesRegex(qmp.QmpError, "not admitted"):
                        client.execute("quit")

    def test_invalid_greeting_closes_without_command_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "qmp.sock"
            with FakeQmpServer(path, greeting={"notQmp": {}}):
                with self.assertRaisesRegex(qmp.QmpError, "greeting"):
                    with qmp.QmpClient(path, timeout_seconds=2):
                        self.fail("invalid greeting unexpectedly admitted")

    def test_atomic_output_is_private_and_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "normal.json"
            qmp.atomic_output(output, "{}\n")
            self.assertEqual(0o600, output.stat().st_mode & 0o777)

            target = root / "target"
            target.write_text("do-not-touch", encoding="utf-8")
            symlink = root / "output.json"
            symlink.symlink_to(target)
            with self.assertRaisesRegex(qmp.QmpError, "symlink"):
                qmp.atomic_output(symlink, "{}\n")
            self.assertEqual("do-not-touch", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
