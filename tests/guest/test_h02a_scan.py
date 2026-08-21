#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
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
    def remote_value(self, *, passed: bool = True, findings: list[dict[str, str]] | None = None) -> dict[str, object]:
        return {
            "passed": passed,
            "findings": findings or [],
            "scannedPaths": list(scan.REMOTE_SCANNED_PATHS),
            "stats": {"files": 4, "bytes": 20, "processes": 3},
        }

    def test_reviewed_placeholder_code_is_not_a_secret_value(self) -> None:
        data = b"NODEHOST_BOOTSTRAP_TOKEN=${NODEHOST_BOOTSTRAP_TOKEN:?missing}\ncallback_capability=$(jq -r .callback_capability)\n"
        self.assertEqual([], scan.pattern_findings(data, "vendor-data"))

    def test_real_secret_shapes_are_reported_without_secret_values(self) -> None:
        bootstrap_name = b"NODEHOST_" + b"BOOTSTRAP_TOKEN="
        bootstrap_value = b"abcdefgh" + b"ijklmnop"
        tailscale_value = b"tskey-" + b"auth-" + (b"A" * 16)
        callback_name = b'"callback_' + b'capability":"'
        callback_value = b"B" * 16
        data = (
            bootstrap_name
            + bootstrap_value
            + b"\n"
            + tailscale_value
            + b"\n"
            + callback_name
            + callback_value
            + b'"\n'
        )
        findings = scan.pattern_findings(data, "guest-state")
        self.assertEqual(
            [
                {"path": "guest-state", "category": "tailscale-key"},
                {"path": "guest-state", "category": "bootstrap-token"},
                {"path": "guest-state", "category": "callback-capability"},
            ],
            findings,
        )
        serialized = json.dumps(findings)
        self.assertNotIn(bootstrap_value.decode(), serialized)
        self.assertNotIn(callback_value.decode(), serialized)

    def test_remote_subcommand_runs_from_stdin_without_a_source_path(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-", "remote"],
            input=HELPER.read_text(encoding="utf-8"),
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertEqual(list(scan.REMOTE_SCANNED_PATHS), value["scannedPaths"])
        self.assertEqual({"bytes", "files", "processes"}, set(value["stats"]))

    def test_combine_scans_exact_seed_sources_and_remote_result(self) -> None:
        local = ROOT / ".local"
        local.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local, prefix="qemu-lab-scan-test-") as temporary:
            state = Path(temporary)
            for name in ("vendor-data", "user-data", "meta-data"):
                (state / name).write_text("safe reviewed input\n", encoding="utf-8")
            remote = state / "remote.json"
            remote.write_text(json.dumps(self.remote_value()), encoding="utf-8")
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
                    self.remote_value(
                        passed=False,
                        findings=[{"path": "/run/secret", "category": "bootstrap-token"}],
                    )
                ),
                encoding="utf-8",
            )
            result = scan.combine_scan(state, "qemu-restart", remote)
            self.assertFalse(result["passed"])
            self.assertEqual("bootstrap-token", result["findings"][0]["category"])

    def test_inconsistent_remote_pass_flag_is_rejected(self) -> None:
        local = ROOT / ".local"
        local.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local, prefix="qemu-lab-scan-test-") as temporary:
            state = Path(temporary)
            for name in ("vendor-data", "user-data", "meta-data"):
                (state / name).write_text("safe\n", encoding="utf-8")
            remote = state / "remote.json"
            remote.write_text(json.dumps(self.remote_value(passed=False)), encoding="utf-8")
            with self.assertRaisesRegex(scan.ScanError, "pass flag disagrees"):
                scan.combine_scan(state, "initial", remote)

    def test_remote_scope_drift_is_rejected(self) -> None:
        local = ROOT / ".local"
        local.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local, prefix="qemu-lab-scan-test-") as temporary:
            state = Path(temporary)
            for name in ("vendor-data", "user-data", "meta-data"):
                (state / name).write_text("safe\n", encoding="utf-8")
            value = self.remote_value()
            value["scannedPaths"] = ["/tmp"]
            remote = state / "remote.json"
            remote.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(scan.ScanError, "scope differs"):
                scan.combine_scan(state, "initial", remote)


if __name__ == "__main__":
    unittest.main()
