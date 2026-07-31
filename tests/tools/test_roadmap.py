from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/roadmap"))

import commands  # noqa: E402
import live  # noqa: E402
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
        by_id["FND-01"]["milestone"] = by_id["WEB-04"]["milestone"]
        by_id["FND-01"]["blockedBy"] = ["WEB-04"]
        by_id["WEB-04"]["blockedBy"] = ["FND-01"]
        with self.assertRaisesRegex(roadmap.RoadmapError, "roadmap dependency cycle"):
            roadmap.validate_seed(altered)

    def test_live_projection_keeps_authorization_and_acceptance_separate(self) -> None:
        graph = sync.enrich(roadmap.seed_graph(self.seed), self.seed)
        snapshot, index = roadmap.derive_snapshot(graph, fallback=True, generated_at="2026-07-31T00:00:00Z")
        sync.project_pull_requests(snapshot, index, graph)
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

    def test_edited_visible_summary_is_live_truth(self) -> None:
        issue = {
            "number": 22,
            "body": """<!-- roadmap-id: WEB-04 -->
<!-- public-summary: stale hidden text -->
<!-- task-packet: agents/tasks/WEB04/task.md -->

## Public summary

This edited visible summary is now the authoritative public wording.

## Observable outcome

Something useful happens.
""",
        }
        item_id, task, summary, pulls = live.parse_issue_body(issue)
        self.assertEqual("WEB-04", item_id)
        self.assertEqual("agents/tasks/WEB04/task.md", task)
        self.assertEqual("This edited visible summary is now the authoritative public wording.", summary)
        self.assertEqual([], pulls)

    def test_live_graph_requires_exact_metadata_and_no_cycles(self) -> None:
        graph = sync.enrich(roadmap.seed_graph(self.seed), self.seed)
        live.validate_graph(graph)

        duplicate_area = copy.deepcopy(graph)
        duplicate_area["items"]["WEB-04"]["labels"].append("area:testing")
        with self.assertRaisesRegex(roadmap.RoadmapError, "exactly one area"):
            live.validate_graph(duplicate_area)

        cycle = copy.deepcopy(graph)
        cycle["items"]["WEB-00"]["blockedBy"] = ["WEB-04"]
        with self.assertRaisesRegex(roadmap.RoadmapError, "dependency cycle"):
            live.validate_graph(cycle)

    def test_pull_request_state_is_separate_from_work_state(self) -> None:
        graph = sync.enrich(roadmap.seed_graph(self.seed), self.seed)
        snapshot, index = roadmap.derive_snapshot(graph, fallback=True, generated_at="2026-07-31T00:00:00Z")
        sync.project_pull_requests(snapshot, index, graph)
        fnd06 = next(item for item in snapshot["items"] if item["id"] == "FND-06")
        self.assertEqual("review", fnd06["workState"])
        self.assertEqual([20], [value["number"] for value in fnd06["pullRequests"]])
        self.assertEqual("unknown", fnd06["pullRequests"][0]["state"])

    def test_structural_errors_are_not_transport_errors(self) -> None:
        graph = sync.enrich(roadmap.seed_graph(self.seed), self.seed)
        graph["items"].pop("WEB-04")
        with self.assertRaises(roadmap.RoadmapError) as caught:
            live.validate_graph(graph)
        self.assertNotIsInstance(caught.exception, live.RoadmapTransportError)

    def test_check_rejects_seed_only_projection(self) -> None:
        with mock.patch.object(sys, "argv", ["sync.py", "--check", "--seed-only"]):
            with self.assertRaisesRegex(roadmap.RoadmapError, "cannot be combined"):
                sync.main()


if __name__ == "__main__":
    unittest.main()
