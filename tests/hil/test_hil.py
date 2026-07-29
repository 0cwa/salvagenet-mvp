from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.hil.config import ConfigError, HilConfig
from tests.hil.evidence import redact
from tests.hil.scenarios import next_generation
from tests.hil.adapters import HeadscaleLab


class HilConfigTest(unittest.TestCase):
    def test_resolves_relative_paths_against_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "hil.json"
            path.write_text(
                json.dumps(
                    {
                        "device": {
                            "serial": "abc",
                            "packageName": "pkg",
                            "supervisorComponent": "pkg/service",
                        },
                        "paths": {
                            "apk": "out.apk",
                            "controller": "ctl",
                            "controllerConfig": "ctl.json",
                        },
                    }
                ),
                encoding="utf-8",
            )
            config = HilConfig.load(root, str(path))
            self.assertEqual(root / "out.apk", config.apk_path)
            self.assertEqual("abc", config.device_serial)

    def test_missing_required_field_is_clear(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "hil.json"
            path.write_text("{}", encoding="utf-8")
            config = HilConfig.load(root, str(path))
            with self.assertRaisesRegex(ConfigError, "device.serial"):
                _ = config.device_serial


class PureHelpersTest(unittest.TestCase):
    def test_next_generation_advances_current(self) -> None:
        template = {"generation": 2}
        self.assertEqual(8, next_generation([{"generation": 7}], template))

    def test_redacts_bearer_and_capability(self) -> None:
        value = redact('Authorization: Bearer abc123 capability="xyz"')
        self.assertNotIn("abc123", value)
        self.assertNotIn("xyz", value)

    def test_headscale_name_search_is_recursive(self) -> None:
        value = {"nodes": [{"name": "salvagenet-phone-01-host"}]}
        self.assertTrue(HeadscaleLab._contains_name(value, "phone-01-host"))
        self.assertFalse(HeadscaleLab._contains_name(value, "other-node"))


if __name__ == "__main__":
    unittest.main()
