import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PodroidKnowledgeFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.argv = (ROOT / "tests/qemu/podroid-baseline.argv").read_text()
        self.invariants = json.loads((ROOT / "tests/qemu/invariants.json").read_text())
        self.metadata = json.loads((ROOT / "tests/qemu/podroid-baseline.metadata.json").read_text())

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

    def test_upstream_snapshot_tracks_the_pinned_source(self) -> None:
        lock = json.loads((ROOT / "android/upstream/podroid.lock").read_text())
        self.assertEqual(lock["commit"], self.metadata["upstreamCommit"])
        self.assertEqual(lock["release"], self.metadata["upstreamRelease"])

    def test_production_golden_only_applies_the_documented_path_and_forward_changes(self) -> None:
        def argv(path: str) -> list[str]:
            return [
                line for line in (ROOT / path).read_text().splitlines()
                if line and not line.startswith("#")
            ]

        upstream = argv(self.metadata["upstreamSnapshot"])
        expected = []
        for argument in upstream:
            if argument.startswith("user,id=net0,"):
                argument = "user,id=net0,ipv6=off,hostfwd=tcp:127.0.0.1:19922-:22"
            else:
                for name in ("vmlinuz-virt", "initrd.img", "alpine-rootfs.squashfs"):
                    argument = argument.replace("${FILES}/" + name, "${FILES}/artifacts/" + name)
                argument = argument.replace("${FILES}/", "${FILES}/vms/default/")
            expected.append(argument)
        self.assertEqual(expected, argv(self.metadata["productionGolden"]))


if __name__ == "__main__":
    unittest.main()
