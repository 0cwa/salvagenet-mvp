#!/usr/bin/env python3
"""Validate the task DAG, packet completeness, and parallel path ownership."""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DAG = json.loads((ROOT / "agents/task-dag.json").read_text(encoding="utf-8"))


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
    """Conservatively identify overlapping ownership patterns.

    Task paths are repository-relative and intentionally simple. Prefix checks
    catch broad-tree overlaps; fnmatch catches exact-file/glob combinations.
    False positives are preferable to overnight write conflicts.
    """

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


def main() -> int:
    tasks = DAG["tasks"]
    ids = {task["id"] for task in tasks}
    assert len(ids) == len(tasks), "duplicate task ID"

    for task in tasks:
        unknown = set(task["dependsOn"]) - {"BASE_MVP_PASS"} - ids
        assert not unknown, f"{task['id']} has unknown dependencies: {sorted(unknown)}"
        packet = ROOT / "agents/tasks" / task["id"]
        for name in ("task.md", "context.list", "allowed-paths.txt", "README.md"):
            assert (packet / name).is_file(), f"{task['id']} missing {name}"
        assert read_patterns(task["id"]), f"{task['id']} has no allowed paths"

    # Cycle check, ignoring the virtual acceptance gate.
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

    # Parallel tasks must not own overlapping write paths.
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

    print("task DAG and parallel path ownership OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
