import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PodroidKnowledgeFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.argv = (ROOT / "tests/qemu/podroid-baseline.argv").read_text()
        self.invariants = json.loads((ROOT / "tests/qemu/invariants.json").read_text())

    def test_required_tokens_and_loopback_forward_are_retained(self) -> None:
        for token in self.invariants["requiredTokens"]:
            self.assertIn(token, self.argv)
        self.assertIn(self.invariants["managementForwardPrefix"], self.argv)

    def test_podroid_disk_order_is_documented(self) -> None:
        state = self.argv.index("file=${FILES}/vms/default/storage.img")
        lower = self.argv.index("file=${FILES}/vms/default/artifacts/alpine-rootfs.squashfs")
        self.assertLess(state, lower)
        self.assertIn("id=drive1", self.argv[state : state + 180])
        self.assertIn("id=drive2", self.argv[lower : lower + 180])


if __name__ == "__main__":
    unittest.main()
