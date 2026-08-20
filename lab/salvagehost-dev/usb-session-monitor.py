#!/usr/bin/env python3
"""Event-driven supervisor for one explicit nodehost-dev USB session.

This process is started by the root-only VM wrapper and is never enabled as a
timer.  It watches the exact USB udev stream and libvirt lifecycle events.  A
matching USB re-enumeration invokes the reconciler's mutating event mode; a
domain shutdown/crash removes the /run session so qemu access cannot outlive
the VM under normal lifecycle paths.
"""

from __future__ import annotations

import argparse
import os
import re
import selectors
import signal
import subprocess
import sys
from pathlib import Path


SERIAL = "5VT7N16607000293"
VENDOR = "18d1"
PRODUCT = "4ee7"
PORT = "3-2"
TERMINAL_LIFECYCLE = re.compile(r"\bStopped\s+(?:Shutdown|Destroyed|Crashed)\b", re.IGNORECASE)


def read_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.isupper() or key in values:
            raise ValueError(f"invalid USB config line: {raw!r}")
        values[key] = value
    required = {
        "SALVAGEHOST_USB_VM_NAME",
        "SALVAGEHOST_USB_SERIAL",
        "SALVAGEHOST_USB_VENDOR_ID",
        "SALVAGEHOST_USB_PRODUCT_ID",
        "SALVAGEHOST_USB_PHYSICAL_PORT",
        "SALVAGEHOST_USB_LIBVIRT_URI",
    }
    missing = sorted(required - values.keys())
    if missing:
        raise ValueError(f"missing config keys: {', '.join(missing)}")
    if (
        values["SALVAGEHOST_USB_VM_NAME"] != "nodehost-dev"
        or values["SALVAGEHOST_USB_SERIAL"] != SERIAL
        or values["SALVAGEHOST_USB_VENDOR_ID"].lower() != VENDOR
        or values["SALVAGEHOST_USB_PRODUCT_ID"].lower() != PRODUCT
        or values["SALVAGEHOST_USB_PHYSICAL_PORT"] != PORT
        or values["SALVAGEHOST_USB_LIBVIRT_URI"] != "qemu:///system"
    ):
        raise ValueError("config is not the authorized nodehost-dev HIL target")
    return values


def udev_event_matches(properties: dict[str, str]) -> bool:
    devpath = properties.get("DEVPATH", "").rstrip("/")
    return (
        properties.get("ACTION") in {"add", "change"}
        and properties.get("SUBSYSTEM") == "usb"
        and properties.get("DEVTYPE") == "usb_device"
        and properties.get("ID_VENDOR_ID", "").lower() == VENDOR
        and properties.get("ID_MODEL_ID", "").lower() == PRODUCT
        and properties.get("ID_SERIAL_SHORT") == SERIAL
        and devpath.endswith(f"/{PORT}")
    )


def run_reconciler(reconciler: Path, config: Path) -> None:
    command = [str(reconciler), "--event", "--config", str(config)]
    try:
        result = subprocess.run(command, check=False, timeout=60)
    except subprocess.TimeoutExpired:
        print("USB event reconciliation timed out", file=sys.stderr)
        return
    if result.returncode:
        print(f"USB event reconciliation failed with exit {result.returncode}", file=sys.stderr)


def cleanup(reconciler: Path, config: Path) -> None:
    command = [str(reconciler), "--cleanup-session", "--config", str(config)]
    try:
        result = subprocess.run(command, check=False, timeout=30)
    except subprocess.TimeoutExpired:
        print("USB session cleanup timed out", file=sys.stderr)
        return
    if result.returncode:
        print(f"USB session cleanup failed with exit {result.returncode}", file=sys.stderr)


def is_terminal_lifecycle_event(line: str) -> bool:
    """Return whether a libvirt lifecycle line denotes a terminal VM event."""

    return TERMINAL_LIFECYCLE.search(line) is not None


def consume_udev_line(line: str, properties: dict[str, str]) -> bool:
    """Consume one udev property line and report complete matching events."""

    if not line:
        matches = udev_event_matches(properties)
        properties.clear()
        return matches
    if "=" in line:
        name, value = line.split("=", 1)
        properties[name] = value
    return False


def drain_stream(stream: object, buffer: bytearray) -> tuple[list[str], bool]:
    """Read every currently available chunk and return complete newline lines."""

    lines: list[str] = []
    eof = False
    fd = stream.fileno()  # type: ignore[attr-defined]
    while True:
        try:
            chunk = os.read(fd, 65536)
        except BlockingIOError:
            break
        if not chunk:
            eof = True
            break
        buffer.extend(chunk)
        while b"\n" in buffer:
            raw_line, _, remainder = buffer.partition(b"\n")
            buffer[:] = remainder
            lines.append(raw_line.rstrip(b"\r").decode("utf-8", errors="replace"))
    return lines, eof


def unregister_stream(selector: selectors.BaseSelector, stream: object) -> None:
    """Remove an EOF stream without making the selector spin on it."""

    try:
        selector.unregister(stream)  # type: ignore[arg-type]
    except KeyError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--reconciler", type=Path, default=Path(__file__).with_name("reconcile-usb-device.sh"))
    args = parser.parse_args()
    try:
        config = read_config(args.config)
    except (OSError, ValueError) as exc:
        print(f"usb-session-monitor: {exc}", file=sys.stderr)
        return 2

    marker = Path("/run/salvagehost/nodehost-dev-usb.active")
    if not marker.exists():
        return 0

    stop = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    udev = subprocess.Popen(
        ["udevadm", "monitor", "--udev", "--property", "--subsystem-match=usb"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )
    lifecycle = subprocess.Popen(
        [
            "virsh",
            "-c",
            config["SALVAGEHOST_USB_LIBVIRT_URI"],
            "event",
            "--domain",
            config["SALVAGEHOST_USB_VM_NAME"],
            "--event",
            "lifecycle",
            "--loop",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )
    selector = selectors.DefaultSelector()
    assert udev.stdout is not None
    assert lifecycle.stdout is not None
    os.set_blocking(udev.stdout.fileno(), False)
    os.set_blocking(lifecycle.stdout.fileno(), False)
    selector.register(udev.stdout, selectors.EVENT_READ, "udev")
    selector.register(lifecycle.stdout, selectors.EVENT_READ, "lifecycle")
    buffers = {udev.stdout: bytearray(), lifecycle.stdout: bytearray()}
    properties: dict[str, str] = {}

    try:
        while not stop and marker.exists() and selector.get_map():
            events = selector.select(timeout=1.0)
            if not events:
                continue
            for key, _ in events:
                lines, eof = drain_stream(key.fileobj, buffers[key.fileobj])
                for line in lines:
                    if key.data == "lifecycle":
                        if is_terminal_lifecycle_event(line):
                            cleanup(args.reconciler, args.config)
                            return 0
                        continue
                    if consume_udev_line(line, properties) and marker.exists():
                        run_reconciler(args.reconciler, args.config)
                if eof and key.data == "lifecycle" and buffers[key.fileobj]:
                    line = bytes(buffers[key.fileobj]).decode("utf-8", errors="replace")
                    buffers[key.fileobj].clear()
                    if is_terminal_lifecycle_event(line):
                        cleanup(args.reconciler, args.config)
                        return 0
                if eof:
                    unregister_stream(selector, key.fileobj)
    finally:
        selector.close()
        for process in (udev, lifecycle):
            if process.poll() is None:
                process.terminate()
        for process in (udev, lifecycle):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
