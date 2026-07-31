#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "lab/qemu/scripts/h02a-prepare.py"

spec = importlib.util.spec_from_file_location("nodehost_h02a_prepare", HELPER)
assert spec and spec.loader
h02a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h02a)


class H02ALabTests(unittest.TestCase):
    def test_checked_in_profile_and_image_lock_are_canonical(self) -> None:
        profile = h02a.canonical_profile()
        locked = h02a.immutable_image_lock()
        self.assertEqual("ubuntu-2404-arm64-uefi", profile["metadata"]["id"])
        self.assertEqual(
            "https://cloud-images.ubuntu.com/releases/noble/release-20260725/ubuntu-24.04-server-cloudimg-arm64.img",
            locked["url"],
        )
        self.assertEqual(618098176, locked["sizeBytes"])
        self.assertEqual(
            "2eaec7286c49fdea713dddabcf5012cafa7097a658e916acb48f4bc5fdc8e419",
            locked["sha256"],
        )

    def test_mutable_or_incomplete_image_lock_is_rejected(self) -> None:
        bad = {
            "artifacts": {
                "ubuntu-2404-arm64-cloud": {
                    "source": {
                        "kind": "remote-release",
                        "url": "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-arm64.img",
                    },
                    "sha256": None,
                    "sizeBytes": None,
                }
            }
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "lock.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(h02a.LabError):
                h02a.immutable_image_lock(path)

    def test_test_only_user_data_is_a_non_merging_final_stage_script(self) -> None:
        key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB h02a"
        rendered = h02a.test_user_data(key)
        self.assertTrue(rendered.startswith("#!/bin/sh\nset -eu\n"))
        self.assertIn("NODEHOST_H02A_KEY", rendered)
        self.assertIn("/var/lib/nodehost/h02a-ready", rendered)
        self.assertIn("PasswordAuthentication no", rendered)
        self.assertIn("KbdInteractiveAuthentication no", rendered)
        self.assertIn("PermitRootLogin no", rendered)
        for forbidden in (
            "#cloud-config",
            "users:",
            "packages:",
            "write_files:",
            "runcmd:",
            "bootstrap.env",
            "BOOTSTRAP_TOKEN",
            "METADATA_BASE",
            "tailscale",
            "headscale",
            "tskey-",
        ):
            self.assertNotIn(forbidden, rendered.lower() if forbidden.islower() else rendered)

    def test_qemu_plan_is_closed_and_matches_profile_contract(self) -> None:
        profile = h02a.canonical_profile()
        state = Path("/tmp/nodehost-h02a-test")
        with mock.patch.object(h02a, "require_command", side_effect=lambda name: f"/usr/bin/{name}"):
            command = h02a.qemu_command(profile, state, 2222)
        joined = "\n".join(command)
        self.assertIn("-machine\nvirt", joined)
        self.assertIn("-cpu\nmax", joined)
        self.assertIn("-accel\ntcg,thread=multi", joined)
        self.assertIn("if=pflash,format=raw,readonly=on", joined)
        self.assertIn("id=system,format=qcow2", joined)
        self.assertIn("id=data,format=raw", joined)
        self.assertIn("id=seed,format=raw,readonly=on", joined)
        self.assertIn("hostfwd=tcp:127.0.0.1:2222-:22", joined)
        self.assertIn("virtio-blk-pci,drive=system", joined)
        self.assertIn("virtio-blk-pci,drive=data", joined)
        self.assertIn("virtio-net-pci,netdev=net0", joined)
        self.assertNotIn("backing", joined)
        self.assertNotIn("-kernel", command)
        self.assertNotIn("-append", command)
        normalized = h02a.normalized_command(command, state)
        self.assertTrue(any("$STATE/system.qcow2" in value for value in normalized))

    def test_preparation_and_pin_entry_points_do_not_use_mutable_current(self) -> None:
        pin = (ROOT / "tools/profiles/pin-ubuntu-image.sh").read_text(encoding="utf-8")
        prepare = (ROOT / "lab/qemu/scripts/prepare.sh").read_text(encoding="utf-8")
        start = (ROOT / "lab/qemu/scripts/start.sh").read_text(encoding="utf-8")
        self.assertNotIn("/current/", pin)
        self.assertIn("explicit immutable Ubuntu release date is required", pin)
        self.assertIn("h02a-prepare.py", prepare)
        self.assertIn("qemu-command.json", start)
        self.assertNotIn("qemu-system-aarch64 \\", start)
        for script in (
            ROOT / "tools/profiles/pin-ubuntu-image.sh",
            ROOT / "lab/qemu/scripts/prepare.sh",
            ROOT / "lab/qemu/scripts/start.sh",
        ):
            subprocess.run(["bash", "-n", str(script)], check=True)


if __name__ == "__main__":
    unittest.main()
