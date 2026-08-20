#!/usr/bin/env python3
"""Deterministic, host-mutation-free tests for usb-session-monitor.py."""

from __future__ import annotations

import importlib.util
import os
import selectors
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("usb-session-monitor.py")
SPEC = importlib.util.spec_from_file_location("usb_session_monitor", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)


MATCHING_UDEV_LINES = [
    "ACTION=add",
    "SUBSYSTEM=usb",
    "DEVTYPE=usb_device",
    "ID_VENDOR_ID=18d1",
    "ID_MODEL_ID=4ee7",
    "ID_SERIAL_SHORT=5VT7N16607000293",
    "DEVPATH=/devices/pci0000:00/3-2",
    "",
]


class UsbSessionMonitorTests(unittest.TestCase):
    def test_terminal_lifecycle_requires_stopped_and_reason(self) -> None:
        self.assertTrue(monitor.is_terminal_lifecycle_event("Stopped Shutdown"))
        self.assertTrue(monitor.is_terminal_lifecycle_event("domain: Stopped Destroyed"))
        self.assertTrue(monitor.is_terminal_lifecycle_event("Stopped Crashed"))
        self.assertFalse(monitor.is_terminal_lifecycle_event("Shutdown Finished"))
        self.assertFalse(monitor.is_terminal_lifecycle_event("Started"))
        self.assertFalse(monitor.is_terminal_lifecycle_event("Shutdown"))

    def test_udev_blank_lines_preserve_event_boundaries(self) -> None:
        properties: dict[str, str] = {}
        matches = [monitor.consume_udev_line(line, properties) for line in MATCHING_UDEV_LINES]
        self.assertEqual(matches[-1], True)
        self.assertEqual(properties, {})

        matches = [monitor.consume_udev_line(line, properties) for line in ["ACTION=remove", ""]]
        self.assertEqual(matches[-1], False)
        self.assertEqual(properties, {})

    def test_drain_reads_all_available_lines_and_keeps_partial_line(self) -> None:
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"ACTION=add\n\nStopped Shutdown\npartial")
            os.close(write_fd)
            write_fd = -1
            read_stream = os.fdopen(read_fd, "rb", buffering=0)
            os.set_blocking(read_stream.fileno(), False)
            buffer = bytearray()
            lines, eof = monitor.drain_stream(read_stream, buffer)
            self.assertTrue(eof)
            self.assertEqual(lines, ["ACTION=add", "", "Stopped Shutdown"])
            self.assertEqual(bytes(buffer), b"partial")
            read_stream.close()
        finally:
            if write_fd != -1:
                os.close(write_fd)

    def test_eof_unregisters_stream(self) -> None:
        read_fd, write_fd = os.pipe()
        selector = selectors.DefaultSelector()
        try:
            read_stream = os.fdopen(read_fd, "rb", buffering=0)
            os.set_blocking(read_stream.fileno(), False)
            selector.register(read_stream, selectors.EVENT_READ, "fake")
            os.close(write_fd)
            write_fd = -1
            events = selector.select(timeout=0)
            self.assertEqual(len(events), 1)
            _, eof = monitor.drain_stream(events[0][0].fileobj, bytearray())
            self.assertTrue(eof)
            monitor.unregister_stream(selector, read_stream)
            self.assertFalse(selector.get_map())
            self.assertFalse(selector.select(timeout=0))
            read_stream.close()
        finally:
            selector.close()
            if write_fd != -1:
                os.close(write_fd)


if __name__ == "__main__":
    unittest.main()
