from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nodehost_mvp.config import ControllerConfig


class ConfigTest(unittest.TestCase):
    def write_config(self, directory: str, data: dict[str, object]) -> Path:
        path = Path(directory) / "controller.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_load_and_resolve_relative_ca(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ca = Path(directory) / "ca.pem"
            ca.write_text("placeholder", encoding="utf-8")
            path = self.write_config(
                directory,
                {
                    "endpoint": "https://100.64.0.1:7443",
                    "controllerCapability": "x" * 32,
                    "tls": {"caFile": "ca.pem"},
                },
            )
            config = ControllerConfig.load(str(path))
            self.assertEqual(config.endpoint, "https://100.64.0.1:7443")
            self.assertEqual(config.ca_file, str(ca.resolve()))

    def test_reject_http(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "endpoint": "http://example.invalid",
                    "controllerCapability": "x" * 32,
                },
            )
            with self.assertRaisesRegex(ValueError, "https"):
                ControllerConfig.load(str(path))

    def test_reject_unimplemented_spki_setting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "endpoint": "https://example.invalid",
                    "controllerCapability": "x" * 32,
                    "tls": {"pinnedSpkiSha256": "a" * 64},
                },
            )
            with self.assertRaisesRegex(ValueError, "unsupported MVP TLS setting"):
                ControllerConfig.load(str(path))

    def test_load_from_environment(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "NODEHOST_ENDPOINT": "https://100.64.0.2:7443",
                "NODEHOST_CONTROLLER_CAPABILITY": "x" * 32,
            },
            clear=True,
        ):
            config = ControllerConfig.load(None)
        self.assertEqual(config.endpoint, "https://100.64.0.2:7443")

    def test_reject_unknown_root_setting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, {
                "endpoint": "https://example.invalid",
                "controllerCapability": "x" * 32,
                "rawArgv": [],
            })
            with self.assertRaisesRegex(ValueError, "unsupported controller setting"):
                ControllerConfig.load(str(path))

    def test_reject_endpoint_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "endpoint": "https://example.invalid/base",
                    "controllerCapability": "x" * 32,
                },
            )
            with self.assertRaisesRegex(ValueError, "must not contain a path"):
                ControllerConfig.load(str(path))


if __name__ == "__main__":
    unittest.main()
