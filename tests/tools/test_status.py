import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("nodehost_status_tested", ROOT / "tools/status/generate.py")
assert SPEC is not None and SPEC.loader is not None
STATUS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STATUS
SPEC.loader.exec_module(STATUS)


class StatusGenerationTest(unittest.TestCase):
    def test_current_ledger_has_expected_base_and_mvp_plus_shape(self):
        gates = STATUS.parse_ledger(ROOT / "docs/roadmap/acceptance-ledger.md")
        self.assertEqual(20, len([gate for gate in gates if gate.id.startswith("B")]))
        self.assertEqual(4, len([gate for gate in gates if gate.id.startswith("U")]))
        self.assertEqual(10, len([gate for gate in gates if gate.id.startswith("B") and gate.status == "PASS"]))

    def test_readme_summary_is_idempotent(self):
        gates = STATUS.parse_ledger(ROOT / "docs/roadmap/acceptance-ledger.md")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        once = STATUS.replace_readme_block(readme, STATUS.summary_block(gates))
        twice = STATUS.replace_readme_block(once, STATUS.summary_block(gates))
        self.assertEqual(once, twice)
        self.assertIn("10/20 base gates passed", once)

    def test_status_links_are_relative_to_docs_root(self):
        gates = STATUS.parse_ledger(ROOT / "docs/roadmap/acceptance-ledger.md")
        rendered = STATUS.status_document(gates)
        self.assertIn("../evidence/gates/B02.json", rendered)
        self.assertNotIn("../../evidence/gates/B02.json", rendered)


if __name__ == "__main__":
    unittest.main()
