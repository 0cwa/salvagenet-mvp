#!/usr/bin/env python3
"""Validate active-phase metadata, packet completeness, dependencies, and path ownership."""
from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAG = json.loads((ROOT / "agents/task-dag.json").read_text(encoding="utf-8"))
REGISTRY = json.loads((ROOT / "agents/task-registry.json").read_text(encoding="utf-8"))
SPECIAL_DEPENDENCIES = {"BASE_MVP_PASS"}
ACTIVE_STATUSES = {"PLANNED", "IN_PROGRESS", "MERGE_READY"}
REQUIRED_PACKET_HEADINGS = (
    "## Status",
    "## Phase-start review",
    "## Compatibility policy",
    "## Acceptance criteria",
    "## Phase-end verification",
    "## Handoff",
)


@dataclass(frozen=True)
class OwnedPattern:
    task_id: str
    pattern: str

    @property
    def static_prefix(self) -> str:
        wildcard_positions = [
            position
            for marker in ("*", "?", "[")
            if (position := self.pattern.find(marker)) >= 0
        ]
        end = min(wildcard_positions) if wildcard_positions else len(self.pattern)
        return self.pattern[:end].rstrip("/")


def read_patterns(task_id: str) -> list[str]:
    path = ROOT / "agents/tasks" / task_id / "allowed-paths.txt"
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def patterns_overlap(left: OwnedPattern, right: OwnedPattern) -> bool:
    """Conservatively identify overlapping ownership patterns."""
    if left.pattern == right.pattern:
        return True
    if fnmatch.fnmatch(left.static_prefix, right.pattern):
        return True
    if fnmatch.fnmatch(right.static_prefix, left.pattern):
        return True
    if not left.static_prefix or not right.static_prefix:
        return True
    left_prefix = left.static_prefix + "/"
    right_prefix = right.static_prefix + "/"
    return left.static_prefix == right.static_prefix or left_prefix.startswith(
        right_prefix
    ) or right_prefix.startswith(left_prefix)


def validate_phase() -> None:
    phase = DAG.get("phase")
    assert isinstance(phase, dict), "active DAG must declare one phase"
    assert isinstance(phase.get("id"), str) and phase["id"], "phase id is required"
    assert isinstance(phase.get("objective"), str) and phase["objective"], "phase objective is required"
    for key in ("entryCriteria", "exitCriteria"):
        values = phase.get(key)
        assert isinstance(values, list) and values, f"phase {key} must be non-empty"
        assert all(isinstance(value, str) and value.strip() for value in values), (
            f"phase {key} entries must be non-empty strings"
        )


def main() -> int:
    validate_phase()
    tasks = DAG["tasks"]
    ids = {task["id"] for task in tasks}
    assert len(ids) == len(tasks), "duplicate active task ID"
    assert tasks, "active phase must contain at least one task"

    registry_tasks = REGISTRY["tasks"]
    registry_by_id = {task["id"]: task for task in registry_tasks}
    assert len(registry_by_id) == len(registry_tasks), "duplicate registry task ID"
    cycle_status = REGISTRY.get("cycleStatus", {})

    for task in tasks:
        task_id = task["id"]
        assert task_id in registry_by_id, f"active task missing from registry: {task_id}"
        status = registry_by_id[task_id].get("status") or cycle_status.get(task_id)
        assert status in ACTIVE_STATUSES, f"active task {task_id} has inactive status: {status}"
        assert cycle_status.get(task_id) == status, f"registry status disagreement for {task_id}"

        unknown = set(task["dependsOn"]) - SPECIAL_DEPENDENCIES - set(registry_by_id)
        assert not unknown, f"{task_id} has unknown dependencies: {sorted(unknown)}"
        blocked = [
            dependency
            for dependency in task["dependsOn"]
            if dependency not in SPECIAL_DEPENDENCIES
            and dependency not in ids
            and (registry_by_id[dependency].get("status") or cycle_status.get(dependency)) != "MERGED"
        ]
        assert not blocked, f"{task_id} depends on inactive, unmerged tasks: {sorted(blocked)}"

        packet = ROOT / "agents/tasks" / task_id
        for name in ("task.md", "context.list", "allowed-paths.txt", "README.md"):
            assert (packet / name).is_file(), f"{task_id} missing {name}"
        assert read_patterns(task_id), f"{task_id} has no allowed paths"
        task_text = (packet / "task.md").read_text(encoding="utf-8")
        for heading in REQUIRED_PACKET_HEADINGS:
            assert heading in task_text, f"{task_id} missing packet heading: {heading}"

    visiting: set[str] = set()
    done: set[str] = set()
    by_id = {task["id"]: task for task in tasks}

    def visit(task_id: str) -> None:
        if task_id in done:
            return
        assert task_id not in visiting, f"cycle at {task_id}"
        visiting.add(task_id)
        for dependency in by_id[task_id]["dependsOn"]:
            if dependency in by_id:
                visit(dependency)
        visiting.remove(task_id)
        done.add(task_id)

    for task_id in sorted(ids):
        visit(task_id)

    groups: dict[int, list[dict[str, object]]] = {}
    for task in tasks:
        groups.setdefault(int(task["parallelGroup"]), []).append(task)
    for group, members in groups.items():
        for index, left_task in enumerate(members):
            for right_task in members[index + 1 :]:
                for left_pattern in read_patterns(str(left_task["id"])):
                    for right_pattern in read_patterns(str(right_task["id"])):
                        left = OwnedPattern(str(left_task["id"]), left_pattern)
                        right = OwnedPattern(str(right_task["id"]), right_pattern)
                        assert not patterns_overlap(left, right), (
                            f"parallel group {group} path overlap: "
                            f"{left.task_id}:{left.pattern} <> "
                            f"{right.task_id}:{right.pattern}"
                        )

    print("active phase, task status, dependencies, and path ownership OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
