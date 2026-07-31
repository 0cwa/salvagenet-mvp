#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "lab/qemu/scripts/h02a-scan.py"
spec = importlib.util.spec_from_file_location("nodehost_h02a_scan", HELPER)
assert spec and spec.loader
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


class H02AScanTests(unittest.TestCase):
    def test_reviewed_placeholder_code_is_not_a_secret_value(self) -> None:
        data = b"NODEHOST_BOOTSTRAP_TOKEN=${NODEHOST_BOOTSTRAP_TOKEN:?missing}\ncallback_capability=$(jq -r .callback_capability)\n"
        self.assertEqual([], scan.pattern_findings(data, "vendor-data"))

    def test_real_secret_shapes_are_reported_without_secret_values(self) -> None:
        data = b"NODEHOST_BOOTSTRAP_TOKEN=abcdefghijklmnop\ntskey-auth-AAAAAAAAAAAAAAAA\n"
        findings = scan.pattern_findings(data, "guest-state")
        self.assertEqual(
            [
                {"path": "guest-state", "category": "tailscale-key"},
                {"path": "guest-state", "category": "bootstrap-token"},
            ],
            findings,
        )
        self.assertNotIn("abcdefghijklmnop", json.dumps(findings))

    def test_combine_scans_exact_seed_sources_and_remote_result(self) -> None:
        local = ROOT / ".local"
        local.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local, prefix="qemu-lab-scan-test-") as temporary:
            state = Path(temporary)
            for name in ("vendor-data", "user-data", "meta-data"):
                (state / name).write_text("safe reviewed input\n", encoding="utf-8")
            remote = state / "remote.json"
            remote.write_text(
                json.dumps(
                    {
                        "passed": True,
                        "findings": [],
                        "scannedPaths": ["/var/lib/cloud", "/proc/*/environ"],
                        "stats": {"files": 4, "bytes": 20, "processes": 3},
                    }
                ),
                encoding="utf-8",
            )
            result = scan.combine_scan(state, "initial", remote)
            self.assertTrue(result["passed"])
            self.assertEqual([], result["findings"])
            recorded = json.loads((state / "secret-scan-initial.json").read_text(encoding="utf-8"))
            self.assertEqual(result, recorded)
            self.assertIn(str(state / "vendor-data"), recorded["scannedPaths"])

    def test_remote_findings_cannot_be_overridden_by_safe_local_inputs(self) -> None:
        local = ROOT / ".local"
        local.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local, prefix="qemu-lab-scan-test-") as temporary:
            state = Path(temporary)
            for name in ("vendor-data", "user-data", "meta-data"):
                (state / name).write_text("safe\n", encoding="utf-8")
            remote = state / "remote.json"
            remote.write_text(
                json.dumps(
                    {
                        "passed": False,
                        "findings": [{"path": "/run/secret", "category": "bootstrap-token"}],
                        "scannedPaths": ["/run"],
                        "stats": {"files": 1, "bytes": 20, "processes": 1},
                    }
                ),
                encoding="utf-8",
            )
            result = scan.combine_scan(state, "qemu-restart", remote)
            self.assertFalse(result["passed"])
            self.assertEqual("bootstrap-token", result["findings"][0]["category"])


if __name__ == "__main__":
    unittest.main()
