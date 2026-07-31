from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/roadmap"))

import roadmap  # noqa: E402
from catalog import configure_roadmap  # noqa: E402

configure_roadmap(roadmap)

import authorization  # noqa: E402


class RoadmapAuthorizationTests(unittest.TestCase):
    def test_active_dag_task_always_wins(self) -> None:
        desired = authorization.desired_agent_label(
            task_id="H02A",
            active_task_ids={"H02A"},
            current_agent_labels={"agent:queued"},
            issue_open=True,
            registry_statuses={"H02A": "PLANNED"},
        )
        self.assertEqual("agent:active", desired)

    def test_stale_active_label_demotes_to_registry_state(self) -> None:
        desired = authorization.desired_agent_label(
            task_id="H02B",
            active_task_ids={"H02A"},
            current_agent_labels={"agent:active"},
            issue_open=True,
            registry_statuses={"H02B": "QUEUED_REVIEW"},
        )
        self.assertEqual("agent:queued", desired)

    def test_non_active_human_planning_state_is_preserved(self) -> None:
        desired = authorization.desired_agent_label(
            task_id=None,
            active_task_ids={"H02A"},
            current_agent_labels={"agent:hold"},
            issue_open=True,
            registry_statuses={},
        )
        self.assertEqual("agent:hold", desired)

    def test_closed_issue_has_no_default_agent_state(self) -> None:
        desired = authorization.desired_agent_label(
            task_id="WEB04",
            active_task_ids={"H02A"},
            current_agent_labels={"agent:active"},
            issue_open=False,
            registry_statuses={"WEB04": "MERGED"},
        )
        self.assertIsNone(desired)

    def test_reconcile_preserves_non_agent_labels(self) -> None:
        labels = authorization.reconcile_label_names(
            [
                "roadmap",
                "roadmap:public",
                "area:guest",
                "kind:qualification",
                "agent:queued",
            ],
            "agent:active",
        )
        self.assertEqual(
            [
                "agent:active",
                "area:guest",
                "kind:qualification",
                "roadmap",
                "roadmap:public",
            ],
            labels,
        )

    def test_multiple_non_active_states_fail(self) -> None:
        with self.assertRaisesRegex(roadmap.RoadmapError, "multiple non-active"):
            authorization.desired_agent_label(
                task_id=None,
                active_task_ids=set(),
                current_agent_labels={"agent:queued", "agent:hold"},
                issue_open=True,
                registry_statuses={},
            )


if __name__ == "__main__":
    unittest.main()
