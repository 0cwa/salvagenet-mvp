from __future__ import annotations

import json
from pathlib import Path
import unittest


class OpenApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads((Path(__file__).parents[2] / "control/openapi.yaml").read_text())

    def test_every_operation_inherits_authentication(self) -> None:
        self.assertEqual(self.document["security"], [{"controllerCapability": []}])
        for path, item in self.document["paths"].items():
            for method, operation in item.items():
                if method == "parameters": continue
                with self.subTest(path=path, method=method):
                    self.assertNotEqual(operation.get("security"), [])

    def test_collections_and_upload_are_bounded(self) -> None:
        schemas = self.document["components"]["schemas"]
        self.assertEqual(schemas["ImageImport"]["properties"]["expectedSizeBytes"]["maximum"], 64 * 1024**3)
        for name in ("capabilities", "profiles", "images", "vms", "operations"):
            schema = self.document["paths"][f"/v1/{name}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
            self.assertGreater(schema["maxItems"], 0)

    def test_contract_contains_no_execution_escape_hatches(self) -> None:
        rendered = json.dumps(self.document).lower()
        for forbidden in ("rawqmp", "raw qmp", "rawargv", "raw argv", "shellcommand", "kernelargs"):
            self.assertNotIn(forbidden, rendered)


if __name__ == "__main__": unittest.main()
