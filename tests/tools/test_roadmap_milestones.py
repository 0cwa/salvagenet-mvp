from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/roadmap"))

import roadmap  # noqa: E402
from catalog import (  # noqa: E402
    configure_roadmap,
    load_milestone_updates,
    prepare_live_milestone_updates,
)

configure_roadmap(roadmap)


class FakeClient:
    repository = "0cwa/salvagenet-mvp"

    def __init__(self) -> None:
        self.milestones = [
            {
                "number": 3,
                "title": "M1 — Validated MVP",
                "description": "Old description",
                "state": "open",
            }
        ]
        self.calls: list[tuple[str, str, dict]] = []

    def repo_path(self, suffix: str) -> str:
        return suffix

    def paginate(self, path: str):
        if "/milestones?state=all" in path:
            return copy.deepcopy(self.milestones)
        return []

    def call(self, method: str, path: str, payload: dict):
        self.calls.append((method, path, copy.deepcopy(payload)))
        if method == "PATCH" and path == "/milestones/3":
            self.milestones[0].update(payload)
        return object()


class RoadmapMilestoneTests(unittest.TestCase):
    def test_composed_catalog_uses_substrate_milestone_name(self) -> None:
        milestones = {
            value["id"]: value for value in roadmap.load_seed()["milestones"]
        }
        self.assertEqual(
            "M1 — Validated stock-node substrate",
            milestones["validated-mvp"]["title"],
        )
        self.assertIn(
            "M1 — Validated MVP",
            milestones["validated-mvp"]["previousTitles"],
        )

    def test_dry_run_previews_rename_without_duplicate_creation(self) -> None:
        client = FakeClient()
        preview, plan = prepare_live_milestone_updates(
            client,
            load_milestone_updates(),
            apply=False,
            roadmap_module=roadmap,
        )
        values = preview.paginate("/milestones?state=all")
        self.assertEqual(
            "M1 — Validated stock-node substrate", values[0]["title"]
        )
        self.assertEqual([], client.calls)
        self.assertEqual(1, len(plan))
        self.assertIn("rename milestone", plan[0])

    def test_apply_renames_existing_milestone_in_place(self) -> None:
        client = FakeClient()
        returned, plan = prepare_live_milestone_updates(
            client,
            load_milestone_updates(),
            apply=True,
            roadmap_module=roadmap,
        )
        self.assertIs(returned, client)
        self.assertEqual(1, len(client.calls))
        self.assertEqual("PATCH", client.calls[0][0])
        self.assertEqual("/milestones/3", client.calls[0][1])
        self.assertEqual(
            "M1 — Validated stock-node substrate",
            client.milestones[0]["title"],
        )
        self.assertEqual(1, len(plan))


if __name__ == "__main__":
    unittest.main()
