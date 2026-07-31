#!/usr/bin/env python3
from __future__ import annotations

from email import policy
from email.parser import BytesParser
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

    def test_state_cleanup_is_confined_to_repository_local_storage(self) -> None:
        accepted = h02a.validate_state_directory(ROOT / ".local/h02a-test-state")
        self.assertEqual((ROOT / ".local/h02a-test-state").resolve(), accepted)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(h02a.LabError, "must remain under"):
                h02a.validate_state_directory(Path(temporary) / "unsafe-state")

    def test_verified_copy_rejects_symlink_destinations(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".local") as temporary:
            directory = Path(temporary)
            source = directory / "source.bin"
            destination = directory / "destination.bin"
            source.write_bytes(b"verified-boot-input")
            expected = h02a.sha256_file(source)
            self.assertEqual(expected, h02a.copy_verified(source, destination, expected))
            self.assertEqual(source.read_bytes(), destination.read_bytes())
            destination.unlink()
            destination.symlink_to(source)
            with self.assertRaisesRegex(h02a.LabError, "must not be a symlink"):
                h02a.copy_verified(source, destination, expected)

    def test_firmware_symlinks_must_resolve_inside_the_package_root(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".local") as temporary:
            directory = Path(temporary)
            firmware_root = directory / "AAVMF"
            firmware_root.mkdir()
            target = firmware_root / "AAVMF_CODE.no-secboot.fd"
            target.write_bytes(b"uefi-firmware")
            admitted = firmware_root / "AAVMF_CODE.fd"
            admitted.symlink_to(target.name)
            self.assertEqual(target.resolve(), h02a.resolve_firmware_path(admitted, firmware_root))

            outside = directory / "outside.fd"
            outside.write_bytes(b"outside-firmware")
            escaped = firmware_root / "AAVMF_VARS.fd"
            escaped.symlink_to(outside)
            with self.assertRaisesRegex(h02a.LabError, "escapes"):
                h02a.resolve_firmware_path(escaped, firmware_root)

    def test_test_only_user_data_is_multipart_with_an_early_key(self) -> None:
        key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB h02a"
        rendered = h02a.test_user_data(key)
        message = BytesParser(policy=policy.default).parsebytes(rendered.encode("utf-8"))
        self.assertTrue(message.is_multipart())
        self.assertEqual("multipart/mixed", message.get_content_type())
        parts = list(message.iter_parts())
        self.assertEqual(
            ["text/cloud-config", "text/x-shellscript"],
            [part.get_content_type() for part in parts],
        )
        cloud_config = parts[0].get_content()
        final_script = parts[1].get_content()
        self.assertTrue(cloud_config.startswith("#cloud-config\nusers:\n"))
        for expected in (
            "name: nodeadmin",
            "groups: [sudo]",
            "shell: /bin/bash",
            "lock_passwd: false",
            'hashed_passwd: "NP"',
            "ssh_authorized_keys:",
            key,
        ):
            self.assertIn(expected, cloud_config)
        for forbidden in (
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
            self.assertNotIn(forbidden, cloud_config)
        self.assertTrue(final_script.startswith("#!/bin/sh\nset -eu\n"))
        self.assertNotIn("authorized_keys", final_script)
        self.assertIn("/etc/sudoers.d/90-nodehost-h02a", final_script)
        self.assertIn("nodeadmin ALL=(ALL) NOPASSWD:ALL", final_script)
        self.assertIn("visudo -cf /etc/sudoers.d/90-nodehost-h02a", final_script)
        self.assertIn("PasswordAuthentication no", final_script)
        self.assertIn("KbdInteractiveAuthentication no", final_script)
        self.assertIn("PermitRootLogin no", final_script)
        self.assertIn("/var/lib/nodehost/h02a-ready", final_script)
        self.assertEqual(2, rendered.count(f"--{h02a.MIME_BOUNDARY}\n"))
        self.assertTrue(rendered.endswith(f"--{h02a.MIME_BOUNDARY}--\n"))

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
        self.assertIn("virtio-net-pci,netdev=net0,romfile=", command)
        self.assertNotIn("virtio-net-pci,netdev=net0", command)
        self.assertNotIn("backing", joined)
        self.assertNotIn("-kernel", command)
        self.assertNotIn("-append", command)
        normalized = h02a.normalized_command(command, state)
        self.assertTrue(any("$STATE/system.qcow2" in value for value in normalized))

    def test_preparation_and_pin_entry_points_do_not_use_mutable_current(self) -> None:
        pin = (ROOT / "tools/profiles/pin-ubuntu-image.sh").read_text(encoding="utf-8")
        prepare = (ROOT / "lab/qemu/scripts/prepare.sh").read_text(encoding="utf-8")
        start = (ROOT / "lab/qemu/scripts/start.sh").read_text(encoding="utf-8")
        helper = HELPER.read_text(encoding="utf-8")
        self.assertNotIn("/current/", pin)
        self.assertIn("explicit immutable Ubuntu release date is required", pin)
        self.assertIn("h02a-prepare.py", prepare)
        self.assertIn("qemu-command.json", start)
        self.assertNotIn("qemu-system-aarch64 \\", start)
        self.assertNotIn("QEMU_EFI.fd", helper)
        self.assertIn("find_firmware_pair", helper)
        self.assertIn("resolve_firmware_path", helper)
        self.assertIn('"resolvedPath": str(resolved)', helper)
        self.assertIn("sha256_file(system) != lock", helper)
        self.assertIn('"format": "multipart/mixed"', helper)
        self.assertIn('"earlySshKey": True', helper)
        self.assertIn('"qualificationAccountPassword": "unlocked-non-authenticating-NP-sentinel"', helper)
        self.assertIn('"qualificationSudo": "nodeadmin-nopasswd-test-only"', helper)
        self.assertIn('"virtio-net-pci,netdev=net0,romfile="', helper)
        for script in (
            ROOT / "tools/profiles/pin-ubuntu-image.sh",
            ROOT / "lab/qemu/scripts/prepare.sh",
            ROOT / "lab/qemu/scripts/start.sh",
        ):
            subprocess.run(["bash", "-n", str(script)], check=True)


if __name__ == "__main__":
    unittest.main()
