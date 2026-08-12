from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.roadmap.bootstrap import plan
from tools.roadmap.common import (
    ROOT,
    SeedValidationError,
    RoadmapError,
    graph_from_seed,
    index_from_graph,
    load_json,
    load_seed,
    marker_from_body,
    marker_for,
    select_fallback_snapshot,
    snapshot_freshness,
    snapshot_from_graph,
    validate_graph,
    validate_seed,
)
from tools.roadmap.context import context_document


class RoadmapSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seed = load_seed()

    def test_seed_is_complete_and_active_tasks_are_mapped(self) -> None:
        facts = validate_seed(self.seed)
        self.assertEqual(facts["issueCount"], 53)
        self.assertEqual(facts["dependencyCount"], 81)
        self.assertEqual(facts["acceptanceCount"], 24)
        self.assertEqual(facts["taskMappingCount"], 2)

    def assert_invalid(self, mutation) -> None:
        candidate = copy.deepcopy(self.seed)
        mutation(candidate)
        with self.assertRaises(SeedValidationError):
            validate_seed(candidate, check_active_tasks=False)

    def test_duplicate_ids_are_rejected(self) -> None:
        self.assert_invalid(lambda seed: seed["issues"].append(copy.deepcopy(seed["issues"][0])))

    def test_missing_acceptance_coverage_is_rejected(self) -> None:
        self.assert_invalid(lambda seed: seed["acceptanceCoverage"].pop())

    def test_unknown_dependency_is_rejected(self) -> None:
        self.assert_invalid(lambda seed: seed["issues"][1]["dependencies"].append("NOPE-99"))

    def test_later_milestone_dependency_is_rejected(self) -> None:
        def mutate(seed):
            next(issue for issue in seed["issues"] if issue["id"] == "FND-01")["dependencies"].append("WEB-00")
        self.assert_invalid(mutate)

    def test_dependency_cycle_is_rejected(self) -> None:
        def mutate(seed):
            next(issue for issue in seed["issues"] if issue["id"] == "WEB-00")["dependencies"].append("WEB-04")
        self.assert_invalid(mutate)

    def test_invalid_context_path_is_rejected(self) -> None:
        def mutate(seed):
            next(issue for issue in seed["issues"] if issue["id"] == "WEB-04")["contextPaths"] = ["../secrets"]
        self.assert_invalid(mutate)

    def test_active_task_disagreement_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.seed)
        candidate["taskMappings"] = candidate["taskMappings"][:1]
        with self.assertRaises(SeedValidationError):
            validate_seed(candidate)


class RoadmapDerivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = load_seed()
        self.generated_at = "2026-08-12T00:00:00Z"
        self.graph = graph_from_seed(self.seed, generated_at=self.generated_at)

    def test_generation_is_deterministic_and_bounded(self) -> None:
        first = snapshot_from_graph(self.graph)
        second = snapshot_from_graph(graph_from_seed(self.seed, generated_at=self.generated_at))
        self.assertEqual(first, second)
        encoded = json.dumps(first)
        self.assertNotIn("observableOutcome", encoded)
        self.assertNotIn('"body"', encoded)
        self.assertLess(len(encoded.encode()), 60_000)
        self.assertEqual(len(first["milestones"]), 7)
        self.assertEqual(sum(len(item["items"]) for item in first["milestones"]), 53)

    def test_partial_graph_fails_closed(self) -> None:
        partial = copy.deepcopy(self.graph)
        partial["dependencyFetchComplete"] = False
        with self.assertRaises(RoadmapError):
            snapshot_from_graph(partial)

    def test_index_separates_authorization_and_dependency_state(self) -> None:
        index = index_from_graph(self.graph)
        active = next(item for item in index["active"] if item["stableId"] == "WEB-04")
        self.assertEqual(active["authorizationState"], "authorized")
        self.assertTrue(any(item["stableId"] == "WEB-01" for item in index["blocked"]))
        self.assertFalse(index["disagreements"])

    def test_freshness_boundary_and_stale_fallback(self) -> None:
        snapshot = snapshot_from_graph(self.graph)
        fresh_now = datetime(2026, 8, 15, tzinfo=timezone.utc)
        stale_now = datetime(2026, 8, 16, tzinfo=timezone.utc)
        self.assertTrue(snapshot_freshness(snapshot, now=fresh_now)["fresh"])
        self.assertFalse(snapshot_freshness(snapshot, now=stale_now)["fresh"])
        select_fallback_snapshot(snapshot, now=fresh_now)
        with self.assertRaises(RoadmapError):
            select_fallback_snapshot(snapshot, now=stale_now)

    def test_marker_is_stable(self) -> None:
        marker = marker_for("WEB-04")
        self.assertEqual(marker_from_body(marker + "\nbody"), "WEB-04")


class RoadmapBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = load_seed()
        self.issue = next(item for item in self.seed["issues"] if item["id"] == "WEB-04")

    def test_bootstrap_dry_run_is_idempotent_and_reports_drift(self) -> None:
        existing = {"issues": [{"stableId": "WEB-04", "labels": ["roadmap"], "milestone": "M0.5"}]}
        result = plan(self.seed, existing)
        self.assertEqual(result["issues"]["verify"], 1)
        self.assertEqual(result["issues"]["create"], 52)
        self.assertTrue(result["liveRefinementsPreserved"])
        self.assertTrue(result["drift"])

    def test_context_excludes_comments_by_default_and_bounds_debug_comments(self) -> None:
        default = context_document(self.issue)
        self.assertNotIn("DEBUG COMMENTS", default)
        comments_fixture = [
            {"createdAt": "2026-08-12T12:00:00Z", "body": "newest planning note"},
            {"createdAt": "2026-08-12T11:00:00Z", "body": "second planning note"},
            {"createdAt": "2026-08-12T10:00:00Z", "body": "third planning note"},
            {"createdAt": "2026-08-12T09:00:00Z", "body": "fourth planning note"},
            {"createdAt": "2026-08-12T08:00:00Z", "body": "fifth planning note"},
            {"createdAt": "2026-08-12T07:00:00Z", "body": "older note must be excluded"},
        ]
        debug = context_document(self.issue, debug_comments=True, comments=comments_fixture)
        self.assertIn("newest planning note", debug)
        self.assertNotIn("older note must be excluded", debug)
        self.assertLessEqual(len(debug.encode()), 24_000)

    def test_context_file_limit_is_enforced(self) -> None:
        issue = copy.deepcopy(self.issue)
        issue["contextPaths"] = [
            "docs/roadmap/public-roadmap-governance.md", "docs/roadmap/podroid-mvp-alignment.md",
            "GOAL.md", "AGENTS.md", "README.md", "docs/INDEX.md", "website/README.md",
            "docs/development/roadmap-agent-workflow.md", "agents/task-dag.json", "agents/task-registry.json",
            "docs/roadmap/acceptance-ledger.md", "docs/roadmap/post-mvp.md", "docs/architecture/debt-register.md",
        ]
        with self.assertRaises(SystemExit):
            context_document(issue)

    def test_cli_seed_validation_is_offline(self) -> None:
        result = subprocess.run([sys.executable, "tools/roadmap/validate_seed.py"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"valid": true', result.stdout)


if __name__ == "__main__":
    unittest.main()
