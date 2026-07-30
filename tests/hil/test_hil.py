from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from tests.hil.adapters import ControllerCli, HeadscaleLab, SetupBlocked
from tests.hil.config import ConfigError, HilConfig
from tests.hil.evidence import EvidenceRecorder, redact
from tests.hil.lease import DeviceLease
from tests.hil.scenarios import load_artifact_set, next_generation

PROMOTE_PATH = Path(__file__).resolve().parents[2] / "tools/evidence/promote-hil.py"
PROMOTE_SPEC = importlib.util.spec_from_file_location("promote_hil", PROMOTE_PATH)
assert PROMOTE_SPEC and PROMOTE_SPEC.loader
promote_hil = importlib.util.module_from_spec(PROMOTE_SPEC)
PROMOTE_SPEC.loader.exec_module(promote_hil)


class HilConfigTest(unittest.TestCase):
    def _config(self, root: Path, extra: dict | None = None) -> HilConfig:
        value = {
            "device": {"serial": "serial-1234", "packageName": "pkg", "supervisorComponent": "pkg/service"},
            "paths": {"apk": "out.apk", "controller": "ctl", "controllerConfig": "ctl.json"},
        }
        if extra:
            value.update(extra)
        path = root / "hil.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return HilConfig.load(root, str(path))

    def test_resolves_relative_paths_against_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self._config(root)
            self.assertEqual(root / "out.apk", config.apk_path)
            self.assertEqual(["adb"], config.adb_command)

    def test_custom_adb_command_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self._config(root, {"device": {"serial": "serial-1234", "adbCommand": ["remote-adb"], "packageName": "pkg", "supervisorComponent": "pkg/service"}})
            self.assertEqual(["remote-adb"], config.adb_command)

    def test_missing_required_field_is_clear(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "hil.json"
            path.write_text("{}", encoding="utf-8")
            config = HilConfig.load(root, str(path))
            with self.assertRaisesRegex(ConfigError, "device.serial"):
                _ = config.device_serial

    def test_scenario_authorization_requires_explicit_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expiry = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            config = self._config(root, {
                "authorization": {
                    "expiresAt": expiry,
                    "allowedScenarios": ["smoke"],
                    "allowApkInstall": True,
                    "allowProcessKill": False,
                    "allowReboot": False,
                    "allowControllerIsolation": False,
                }
            })
            config.require_scenario_authorization("smoke")
            with self.assertRaisesRegex(ConfigError, "not locally authorized"):
                config.require_scenario_authorization("mvp")


class FakeRunner:
    def __init__(self, root: Path, evidence: EvidenceRecorder | None = None):
        self.root = root
        self.evidence = evidence
        self.commands: list[list[str]] = []
    def run(self, argv: list[str], **_kwargs):
        self.commands.append(argv)
        return type("Result", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()


class PureHelpersTest(unittest.TestCase):
    def test_next_generation_advances_current(self) -> None:
        self.assertEqual(8, next_generation([{"generation": 7}], {"generation": 2}))

    def test_redacts_bearer_capability_serial_and_tailscale_key(self) -> None:
        value = redact(
            'Authorization: Bearer abc123 capability="xyz" serial-1234 tskey-auth-example',
            ("serial-1234",),
        )
        for secret in ("abc123", "xyz", "serial-1234", "tskey-auth-example"):
            self.assertNotIn(secret, value)

    def test_headscale_name_search_requires_exact_label_or_fqdn(self) -> None:
        value = {"nodes": [{"name": "salvagenet-phone-01-host"}, {"hostname": "guest.tail.example."}]}
        self.assertTrue(HeadscaleLab._contains_name(value, "salvagenet-phone-01-host"))
        self.assertTrue(HeadscaleLab._contains_name(value, "guest"))
        self.assertFalse(HeadscaleLab._contains_name(value, "phone-01-host"))
        self.assertFalse(HeadscaleLab._contains_name(value, "other-node"))

    def test_controller_uses_per_run_known_hosts_and_isolation_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "hil.json"
            config_path.write_text(json.dumps({
                "device": {"serial": "serial-1234", "packageName": "pkg", "supervisorComponent": "pkg/service"},
                "paths": {"apk": "out.apk", "controller": "ctl", "controllerConfig": "ctl.json"},
                "authorization": {"allowControllerIsolation": True},
                "resilience": {"controllerOfflineCommand": ["offline"], "controllerOnlineCommand": ["online"]},
            }), encoding="utf-8")
            config = HilConfig.load(root, str(config_path))
            recorder = EvidenceRecorder.create(root / "evidence", "resilience", "a" * 40, "b" * 64, "serial-1234")
            runner = FakeRunner(root, recorder)
            controller = ControllerCli(config, runner)  # type: ignore[arg-type]
            self.assertEqual(recorder.directory / "known_hosts", controller.known_hosts_file)
            self.assertTrue(controller.set_controller_reachable(False))
            self.assertTrue(controller.set_controller_reachable(True))
            self.assertEqual([["offline"], ["online"]], runner.commands)

    def test_device_lease_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with DeviceLease(root, "serial-1234", {"scenario": "smoke"}):
                with self.assertRaisesRegex(SetupBlocked, "already leased"):
                    with DeviceLease(root, "serial-1234", {"scenario": "mvp"}):
                        pass
            with DeviceLease(root, "serial-1234", {"scenario": "smoke"}):
                pass

    def test_artifact_set_verifies_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "image.qcow2"
            payload.write_bytes(b"image")
            import hashlib
            digest = hashlib.sha256(b"image").hexdigest()
            artifact_set = root / "artifacts.json"
            artifact_set.write_text(json.dumps({
                "schemaVersion": 1,
                "artifacts": [{"id": "ubuntu-image", "path": "image.qcow2", "sha256": digest, "sizeBytes": 5}],
            }), encoding="utf-8")
            config_path = root / "hil.json"
            config_path.write_text(json.dumps({
                "device": {"serial": "s", "packageName": "pkg", "supervisorComponent": "pkg/service"},
                "paths": {"apk": "a", "controller": "c", "controllerConfig": "cc"},
                "mvp": {"artifactSet": "artifacts.json"},
            }), encoding="utf-8")
            config = HilConfig.load(root, str(config_path))
            values = load_artifact_set(config)
            self.assertEqual("ubuntu-image", values[0]["id"])


class PromotionTest(unittest.TestCase):
    def _candidate(self, scenario: str, assertions: list[dict]) -> dict:
        return {
            "result": "PASS", "scenario": scenario, "sourceCommit": "a" * 40,
            "evidenceMode": "candidate", "sourceDirty": False, "promotable": True,
            "apkSha256": "b" * 64, "assertions": assertions,
        }

    def test_b17_requires_actual_unavailable_assertion(self) -> None:
        run = self._candidate("resilience", [{"id": "resilience.controller-silent", "passed": True}])
        with self.assertRaisesRegex(ValueError, "controller-unavailable"):
            promote_hil.validate_run("B17", run, "a" * 40)

    def test_b02_promotion_accepts_complete_candidate_smoke_run(self) -> None:
        ids = {"smoke.profile-present", "smoke.one-qemu", "smoke.graceful-stop", "smoke.restart-one-qemu"}
        run = self._candidate("smoke", [{"id": item, "passed": True} for item in ids])
        self.assertEqual(ids, promote_hil.validate_run("B02", run, "a" * 40))

    def test_diagnostic_or_dirty_runs_cannot_promote(self) -> None:
        ids = {"smoke.profile-present", "smoke.one-qemu", "smoke.graceful-stop", "smoke.restart-one-qemu"}
        diagnostic = self._candidate("smoke", [{"id": item, "passed": True} for item in ids])
        diagnostic["evidenceMode"] = "diagnostic"
        diagnostic["promotable"] = False
        with self.assertRaisesRegex(ValueError, "clean candidate"):
            promote_hil.validate_run("B02", diagnostic, "a" * 40)
        dirty = self._candidate("smoke", [{"id": item, "passed": True} for item in ids])
        dirty["sourceDirty"] = True
        dirty["promotable"] = False
        with self.assertRaisesRegex(ValueError, "clean candidate"):
            promote_hil.validate_run("B02", dirty, "a" * 40)


if __name__ == "__main__":
    unittest.main()
