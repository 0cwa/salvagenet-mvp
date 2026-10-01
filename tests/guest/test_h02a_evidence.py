#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "lab/qemu/scripts/h02a-evidence.py"
spec = importlib.util.spec_from_file_location("nodehost_h02a_evidence", HELPER)
assert spec and spec.loader
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)

BOOT_IDS = {
    "initial": "11111111-1111-1111-1111-111111111111",
    "guest-reboot": "22222222-2222-2222-2222-222222222222",
    "qemu-restart": "33333333-3333-3333-3333-333333333333",
}
HOST_KEY = "256 SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA [127.0.0.1]:2222 (ED25519)"


class H02AEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        local = ROOT / ".local"
        local.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=local, prefix="qemu-lab-evidence-test-")
        self.state = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.commit = "a" * 40
        self.base = self.state / evidence.BASE_IMAGE
        self.base.write_bytes(b"immutable-base")
        preflight = {
            "schemaVersion": 1,
            "evidenceClass": "host-qemu-preflight",
            "androidHardwareValidated": False,
            "physicalGateEligible": False,
            "guestMeshValidated": False,
            "source": {"commit": self.commit, "dirtyTracked": False},
            "profile": {
                "id": "ubuntu-2404-arm64-uefi",
                "path": "profiles/ubuntu-2404-arm64-uefi/profile.json",
                "sha256": "1" * 64,
            },
            "vendorData": {
                "path": "profiles/guest-init/ubuntu/vendor-data.yaml",
                "renderedSha256": "2" * 64,
            },
            "testUserData": {
                "format": "multipart/mixed",
                "parts": ["text/cloud-config", "text/x-shellscript"],
                "earlySshKey": True,
                "qualificationAccountPassword": "unlocked-non-authenticating-NP-sentinel",
                "sha256": "3" * 64,
                "qualificationSudo": "nodeadmin-nopasswd-test-only",
            },
            "image": {
                "url": "https://example.invalid/releases/20260725/immutable.img",
                "sha256": evidence.sha256_file(self.base),
                "sizeBytes": self.base.stat().st_size,
            },
            "firmware": {
                "code": {
                    "sourcePath": "/usr/share/AAVMF/AAVMF_CODE.fd",
                    "resolvedPath": "/usr/share/AAVMF/AAVMF_CODE.no-secboot.fd",
                    "sourcePathSymlink": True,
                    "sha256": "4" * 64,
                    "copiedSha256": "4" * 64,
                    "sizeBytes": 4096,
                    "package": "qemu-efi-aarch64=1.0",
                },
                "vars": {
                    "sourcePath": "/usr/share/AAVMF/AAVMF_VARS.fd",
                    "resolvedPath": "/usr/share/AAVMF/AAVMF_VARS.fd",
                    "sourcePathSymlink": False,
                    "sha256": "5" * 64,
                    "copiedSha256": "5" * 64,
                    "sizeBytes": 4096,
                    "package": "qemu-efi-aarch64=1.0",
                },
            },
            "tools": {
                "qemu": {"path": "/usr/bin/qemu-system-aarch64", "version": "qemu", "exitCode": 0},
                "qemuImg": {"path": "/usr/bin/qemu-img", "version": "qemu-img", "exitCode": 0},
                "cloudLocalds": {"path": "/usr/bin/cloud-localds", "version": "cloud-localds", "exitCode": 0},
            },
            "lab": {
                "memoryMiB": 2048,
                "vcpus": 2,
                "sshHost": "127.0.0.1",
                "sshPort": 2222,
                "systemDiskMode": "copied-writable",
                "qemuCommand": ["/usr/bin/qemu-system-aarch64", "-name", "nodehost-h02a"],
            },
        }
        (self.state / "preflight.json").write_text(json.dumps(preflight), encoding="utf-8")
        canary = "tskey-" + "auth-" + ("A" * 16)
        for stage, boot_id in BOOT_IDS.items():
            (self.state / f"qmp-{stage}.json").write_text(
                json.dumps({"running": True, "status": "running"}), encoding="utf-8"
            )
            (self.state / f"secret-scan-{stage}.json").write_text(
                json.dumps({"passed": True, "findings": [], "scannedPaths": ["seed", "guest"]}),
                encoding="utf-8",
            )
            (self.state / f"ssh-auth-{stage}.json").write_text(
                json.dumps(
                    {
                        "keyOnlyLoopbackSsh": True,
                        "rootKeyLoginRejected": True,
                        "passwordOnlyClientRejected": True,
                        "keyboardInteractiveOnlyClientRejected": True,
                        "passwordAuthenticationDisabled": True,
                        "keyboardInteractiveDisabled": True,
                        "rootLoginDisabled": True,
                        "qualificationSudoNoninteractive": True,
                    }
                ),
                encoding="utf-8",
            )
            (self.state / f"cloud-init-{stage}.txt").write_text("status: done\n", encoding="utf-8")
            (self.state / f"sshd-{stage}.txt").write_text(
                "passwordauthentication no\nkbdinteractiveauthentication no\npermitrootlogin no\n",
                encoding="utf-8",
            )
            (self.state / f"readiness-{stage}.txt").write_text("h02a-ready\n", encoding="utf-8")
            (self.state / f"boot-id-{stage}.txt").write_text(boot_id + "\n", encoding="utf-8")
            (self.state / f"host-key-{stage}.txt").write_text(HOST_KEY + "\n", encoding="utf-8")
            (self.state / f"guest-tools-{stage}.txt").write_text(
                "cloud-init: cloud-init 24.1\nopenssh-client: OpenSSH_9.6\nkernel: Linux 6.8 aarch64\n",
                encoding="utf-8",
            )
            for name in evidence.LOG_NAMES:
                content = f"safe log {canary}\n" if name == "serial" else ""
                (self.state / f"{name}-{stage}.log").write_text(content, encoding="utf-8")

    def create(self) -> Path:
        with mock.patch.object(evidence.dt, "datetime", wraps=evidence.dt.datetime) as clock:
            clock.now.return_value = evidence.dt.datetime(2026, 7, 31, 3, 0, tzinfo=evidence.dt.timezone.utc)
            return evidence.create_evidence(self.state)

    def test_create_requires_distinct_stage_evidence_and_redacts_log_tails(self) -> None:
        path = self.create()
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("host-qemu", value["evidenceClass"])
        self.assertFalse(value["androidHardwareValidated"])
        self.assertTrue(value["restartChecks"]["guestRebootChangedBootId"])
        self.assertTrue(value["restartChecks"]["qemuStopStartChangedBootId"])
        self.assertTrue(value["restartChecks"]["sshHostKeyStableAcrossRestarts"])
        self.assertTrue(value["stages"]["initial"]["sshAuthentication"]["qualificationSudoNoninteractive"])
        self.assertEqual(
            "/usr/share/AAVMF/AAVMF_CODE.no-secboot.fd",
            value["preflight"]["firmware"]["code"]["resolvedPath"],
        )
        self.assertEqual(9, len(value["logs"]))
        self.assertIn("[REDACTED]", value["logs"]["initial:serial"]["tail"])
        self.assertNotIn("tskey-" + "auth-", value["logs"]["initial:serial"]["tail"])

    def test_duplicate_boot_id_is_rejected(self) -> None:
        (self.state / "boot-id-qemu-restart.txt").write_text(BOOT_IDS["guest-reboot"] + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "distinct boot IDs"):
            evidence.create_evidence(self.state)

    def test_changed_host_key_is_rejected(self) -> None:
        (self.state / "host-key-qemu-restart.txt").write_text(HOST_KEY.replace("AAAA", "BBBB") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "host key changed"):
            evidence.create_evidence(self.state)

    def test_missing_stage_log_is_rejected(self) -> None:
        (self.state / "qemu.stderr-guest-reboot.log").unlink()
        with self.assertRaisesRegex(evidence.EvidenceError, "log path is missing"):
            evidence.create_evidence(self.state)

    def test_inferred_auth_or_unbounded_scan_is_rejected(self) -> None:
        (self.state / "ssh-auth-initial.json").write_text(json.dumps({"keyOnlyLoopbackSsh": True}), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "closed contract"):
            evidence.create_evidence(self.state)

    def test_unrecorded_qualification_contract_is_rejected(self) -> None:
        original = json.loads((self.state / "preflight.json").read_text(encoding="utf-8"))
        for field in ("qualificationSudo", "qualificationAccountPassword"):
            with self.subTest(field=field):
                value = json.loads(json.dumps(original))
                value["testUserData"].pop(field)
                (self.state / "preflight.json").write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaisesRegex(evidence.EvidenceError, "user-data contract"):
                    evidence.create_evidence(self.state)
        (self.state / "preflight.json").write_text(json.dumps(original), encoding="utf-8")

    def test_missing_resolved_firmware_path_is_rejected(self) -> None:
        value = json.loads((self.state / "preflight.json").read_text(encoding="utf-8"))
        value["firmware"]["code"].pop("resolvedPath")
        (self.state / "preflight.json").write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "firmware identity is invalid"):
            evidence.create_evidence(self.state)

    def test_mismatched_copied_firmware_digest_is_rejected(self) -> None:
        value = json.loads((self.state / "preflight.json").read_text(encoding="utf-8"))
        value["firmware"]["vars"]["copiedSha256"] = "6" * 64
        (self.state / "preflight.json").write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "differs from source"):
            evidence.create_evidence(self.state)

    def test_final_only_ssh_key_contract_is_rejected(self) -> None:
        value = json.loads((self.state / "preflight.json").read_text(encoding="utf-8"))
        value["testUserData"].pop("earlySshKey")
        (self.state / "preflight.json").write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "user-data contract"):
            evidence.create_evidence(self.state)

    def test_finalize_requires_exact_cleanup_and_verified_base(self) -> None:
        path = self.create()
        removed = []
        for entry in list(self.state.iterdir()):
            if entry.name in {evidence.BASE_IMAGE, "evidence"}:
                continue
            removed.append(entry.name)
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        receipt = {
            "schemaVersion": 1,
            "qemuStopped": True,
            "retained": sorted([evidence.BASE_IMAGE, "evidence"]),
            "removed": removed,
        }
        (path.parent / "cleanup.json").write_text(json.dumps(receipt), encoding="utf-8")
        evidence.finalize_cleanup(self.state, path)
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(value["cleanup"]["completed"])
        self.assertEqual(evidence.sha256_file(self.base), value["cleanup"]["baseImageSha256"])

    def test_non_object_evidence_is_rejected_without_a_traceback(self) -> None:
        path = self.create()
        path.write_text("[]\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "not an object"):
            evidence.finalize_cleanup(self.state, path)

    def test_symlinked_evidence_path_is_rejected(self) -> None:
        path = self.create()
        link = self.state / "evidence-link.json"
        link.symlink_to(path)
        with self.assertRaisesRegex(evidence.EvidenceError, "must not be a symlink"):
            evidence.finalize_cleanup(self.state, link)

    def test_dirty_preflight_is_not_reviewable(self) -> None:
        value = json.loads((self.state / "preflight.json").read_text(encoding="utf-8"))
        value["source"]["dirtyTracked"] = True
        (self.state / "preflight.json").write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "clean tracked worktree"):
            evidence.create_evidence(self.state)


if __name__ == "__main__":
    unittest.main()
