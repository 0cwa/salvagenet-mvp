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
            "image": {
                "url": "https://example.invalid/immutable.img",
                "sha256": evidence.sha256_file(self.base),
                "sizeBytes": self.base.stat().st_size,
            },
        }
        (self.state / "preflight.json").write_text(json.dumps(preflight), encoding="utf-8")
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
                        "passwordAuthenticationDisabled": True,
                        "keyboardInteractiveDisabled": True,
                        "rootLoginDisabled": True,
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
            (self.state / f"serial-{stage}.log").write_text(
                "safe log tskey-auth-AAAAAAAAAAAAAAAA\n", encoding="utf-8"
            )

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
        self.assertIn("[REDACTED]", value["logs"]["initial:serial"]["tail"])
        self.assertNotIn("tskey-auth-", value["logs"]["initial:serial"]["tail"])

    def test_duplicate_boot_id_is_rejected(self) -> None:
        (self.state / "boot-id-qemu-restart.txt").write_text(BOOT_IDS["guest-reboot"] + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "distinct boot IDs"):
            evidence.create_evidence(self.state)

    def test_inferred_auth_or_unbounded_scan_is_rejected(self) -> None:
        (self.state / "ssh-auth-initial.json").write_text(json.dumps({"keyOnlyLoopbackSsh": True}), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "closed contract"):
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

    def test_dirty_preflight_is_not_reviewable(self) -> None:
        value = json.loads((self.state / "preflight.json").read_text(encoding="utf-8"))
        value["source"]["dirtyTracked"] = True
        (self.state / "preflight.json").write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "clean tracked worktree"):
            evidence.create_evidence(self.state)


if __name__ == "__main__":
    unittest.main()
