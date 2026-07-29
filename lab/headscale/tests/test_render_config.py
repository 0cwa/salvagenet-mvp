from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/render-config.py"
SPEC = importlib.util.spec_from_file_location("render_config", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderConfigTest(unittest.TestCase):
    def test_rejects_placeholder(self) -> None:
        with self.assertRaisesRegex(ValueError, "placeholder"):
            MODULE.validate_public_url("http://REPLACE_WITH_HOST_LAN_IP:8080")

    def test_rejects_documentation_network(self) -> None:
        with self.assertRaisesRegex(ValueError, "documentation-only"):
            MODULE.validate_public_url("http://192.0.2.10:8080")

    def test_renders_phone_reachable_private_address(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            env_file = temp / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "HEADSCALE_VERSION=0.28.0",
                        "HEADSCALE_PUBLIC_URL=http://192.168.50.10:8080",
                        "HEADSCALE_LISTEN_IP=0.0.0.0",
                        "HEADSCALE_BASE_DOMAIN=nodehost.test",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            output = MODULE.render(root, env_file, temp / "generated")
            text = output.read_text(encoding="utf-8")
            self.assertIn('server_url: "http://192.168.50.10:8080"', text)
            self.assertNotIn("${", text)


if __name__ == "__main__":
    unittest.main()
