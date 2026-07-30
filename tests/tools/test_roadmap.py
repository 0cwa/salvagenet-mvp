from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/roadmap"))

import roadmap  # noqa: E402
import sync  # noqa: E402


class RoadmapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = roadmap.load_seed()

    def test_reviewed_seed_is_complete(self) -> None:
        result = roadmap.validate_seed(self.seed)
        self.assertEqual(7, result["milestones"])
        self.assertEqual(53, result["items"])
        self.assertEqual(24, len(result["acceptanceCoverage"]))
        self.assertGreater(result["dependencies"], 40)

    def test_missing_gate_is_rejected(self) -> None:
        altered = copy.deepcopy(self.seed)
        for item in altered["items"]:
            item["acceptanceIds"] = [value for value in item["acceptanceIds"] if value != "U04"]
        with self.assertRaisesRegex(roadmap.RoadmapError, "acceptance coverage"):
            roadmap.validate_seed(altered)

    def test_dependency_cycle_is_rejected(self) -> None:
        altered = copy.deepcopy(self.seed)
        by_id = {item["id"]: item for item in altered["items"]}
        by_id["FND-01"]["blockedBy"] = ["WEB-04"]
        with self.assertRaisesRegex(roadmap.RoadmapError, "later-milestone|cycle"):
            roadmap.validate_seed(altered)

    def test_live_projection_keeps_authorization_and_acceptance_separate(self) -> None:
        graph = sync.enrich(roadmap.seed_graph(self.seed), self.seed)
        snapshot, index = roadmap.derive_snapshot(graph, fallback=True, generated_at="2026-07-31T00:00:00Z")
        active = {item["id"] for item in index["active"]}
        self.assertEqual({"WEB-04"}, active)
        guest = next(item for item in snapshot["items"] if item["id"] == "GUEST-01")
        self.assertFalse(guest["taskAuthorized"])
        release = next(item for item in snapshot["items"] if item["id"] == "RELEASE-01")
        self.assertEqual(20, len(release["acceptance"]))
        self.assertTrue(any(gate["status"] != "PASS" for gate in release["acceptance"]))

    def test_dependency_clear_does_not_make_issue_ready(self) -> None:
        graph = sync.enrich(roadmap.seed_graph(self.seed), self.seed)
        snapshot, _ = roadmap.derive_snapshot(graph, fallback=True, generated_at="2026-07-31T00:00:00Z")
        ea00 = next(item for item in snapshot["items"] if item["id"] == "EA-00")
        self.assertEqual("queued", ea00["workState"])
        self.assertEqual("clear", ea00["dependencyState"])

    def test_context_is_bounded_and_excludes_comments(self) -> None:
        graph = sync.enrich(roadmap.seed_graph(self.seed), self.seed)
        snapshot, _ = roadmap.derive_snapshot(graph, fallback=True, generated_at="2026-07-31T00:00:00Z")
        text = roadmap.bounded_context(snapshot, "WEB-04", max_files=12, max_bytes=65536)
        self.assertIn("Roadmap context: WEB-04", text)
        self.assertIn("agents/tasks/WEB04/task.md", text)
        self.assertNotIn("Comments", text)
        self.assertLess(len(text.encode("utf-8")), 65536)

    def test_issue_body_contains_stable_machine_markers(self) -> None:
        item = next(value for value in self.seed["items"] if value["id"] == "WEB-04")
        body = roadmap.issue_body(item, "sha256:test")
        self.assertIn("<!-- roadmap-id: WEB-04 -->", body)
        self.assertIn("<!-- task-packet: agents/tasks/WEB04/task.md -->", body)
        self.assertIn("Closing this issue does not change the acceptance ledger", body)


if __name__ == "__main__":
    unittest.main()
