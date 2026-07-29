from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/profiles/render-guest-init.py"
SPEC = importlib.util.spec_from_file_location("guest_init_renderer", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GuestInitRendererTest(unittest.TestCase):
    def test_expands_bootstrap_script_with_yaml_indentation(self) -> None:
        template = ROOT / "profiles/guest-init/ubuntu/vendor-data.yaml"
        rendered = MODULE.render(template, {}, allow_unresolved=True)
        self.assertIn("      #!/usr/bin/env bash", rendered)
        self.assertNotIn("{{INCLUDE:", rendered)

    def test_replaces_deployment_values(self) -> None:
        template = ROOT / "profiles/guest-init/ubuntu/user-data.template.yaml"
        rendered = MODULE.render(
            template,
            {
                "METADATA_BASE": "http://10.0.2.2:8123/n/",
                "BOOTSTRAP_TOKEN": "not-a-live-secret",
            },
            allow_unresolved=False,
        )
        self.assertIn("NODEHOST_METADATA_BASE=http://10.0.2.2:8123/n/", rendered)
        self.assertNotIn("{{", rendered)


if __name__ == "__main__":
    unittest.main()
