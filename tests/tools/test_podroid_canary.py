import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "tools" / "vendor" / "podroid_canary.py"
spec = importlib.util.spec_from_file_location("podroid_canary", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PodroidCanaryTest(unittest.TestCase):
    def test_repository_slug(self):
        self.assertEqual("ExTV/Podroid", m.repository_slug("https://github.com/ExTV/Podroid.git"))
        with self.assertRaises(m.CanaryError):
            m.repository_slug("git@github.com:ExTV/Podroid.git")

    def test_build_runtime_lock_rehashes_candidate_apk(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            apk = root / "candidate.apk"
            payloads = {
                "lib/arm64-v8a/libqemu-system-aarch64.so": b"ELF-candidate",
                "assets/qemu/keymaps/en-us": b"keymap-candidate",
            }
            with zipfile.ZipFile(apk, "w") as archive:
                for name, payload in payloads.items():
                    archive.writestr(name, payload)
            base_lock = {
                "artifacts": [
                    {
                        "apkPath": "lib/arm64-v8a/libqemu-system-aarch64.so",
                        "size": 1,
                        "sha256": "old",
                        "generated": True,
                    },
                    {
                        "apkPath": "assets/qemu/keymaps/en-us",
                        "size": 1,
                        "sha256": "old",
                        "generated": False,
                    },
                ]
            }
            target = {
                "release": "v9.9.9",
                "asset": {
                    "url": "https://example.invalid/Podroid-v9.9.9-release.apk",
                    "name": "Podroid-v9.9.9-release.apk",
                },
            }
            lock = m.build_runtime_lock(base_lock, apk, target)
            self.assertEqual("v9.9.9", lock["source"]["version"])
            self.assertEqual(hashlib.sha256(apk.read_bytes()).hexdigest(), lock["source"]["sha256"])
            by_path = {item["apkPath"]: item for item in lock["artifacts"]}
            for name, payload in payloads.items():
                self.assertEqual(len(payload), by_path[name]["size"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), by_path[name]["sha256"])
            self.assertTrue(by_path["lib/arm64-v8a/libqemu-system-aarch64.so"]["generated"])
            self.assertFalse(by_path["assets/qemu/keymaps/en-us"]["generated"])

    def test_write_report_includes_patch_conflict(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = {
                "track": "main",
                "baseline": {"release": "v1.0.0", "commit": "a" * 40},
                "target": {"release": None, "commit": "b" * 40, "subject": "upstream"},
                "patches": [{"name": "0001.patch", "status": "conflict", "detail": "hunk failed"}],
                "runtime": {"status": "not-applicable"},
            }
            target = Path(temporary)
            m.write_report(report, target)
            summary = (target / "summary.md").read_text()
            self.assertIn("0001.patch", summary)
            self.assertIn("hunk failed", summary)
            parsed = json.loads((target / "report.json").read_text())
            self.assertEqual("conflict", parsed["patches"][0]["status"])


if __name__ == "__main__":
    unittest.main()
