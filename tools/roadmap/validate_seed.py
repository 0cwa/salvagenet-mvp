#!/usr/bin/env python3
"""Validate the reviewed bootstrap seed for the SalvageNet issue roadmap.

The seed is intentionally stricter than an arbitrary list of future ideas. It must
cover the project's current acceptance gates, form an acyclic dependency graph,
and remain consistent with the active agent task. After GitHub Issues are
bootstrapped, Issues become authoritative and this file remains historical input.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
REPOSITORY = "0cwa/salvagenet-mvp"
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{2}$")
HEX_RE = re.compile(r"^[0-9A-Fa-f]{6}$")
GATE_RE = re.compile(r"^(?:B(?:0[1-9]|1[0-9]|20)|U0[1-4])$")
TASK_PACKET_RE = re.compile(r"^agents/tasks/([A-Z][A-Z0-9]*)/task\.md$")

REQUIRED_GATES = {*(f"B{i:02d}" for i in range(1, 21)), *(f"U{i:02d}" for i in range(1, 5))}
REQUIRED_STATES = {"done", "review", "queued", "ready", "active", "hold"}
REQUIRED_VISIBILITIES = {"public", "internal"}
REQUIRED_POLICY = {
    "issuesBecomeAuthoritativeAfterBootstrap": True,
    "futurePhasePlansMustReevaluateQueuedItems": True,
    "issueClosureDoesNotCloseAcceptanceGates": True,
    "activeTaskAuthorizationRemainsIn": "agents/task-dag.json",
}
REQUIRED_ITEM_IDS = {
    "FND-01", "FND-02", "FND-03", "FND-04",
    "WEB-00", "WEB-01", "WEB-02", "WEB-03", "WEB-04", "WEB-05", "WEB-06",
    "GUEST-01", "GUEST-02", "DEVICE-01", "DEVICE-02", "DEVICE-03", "DEVICE-04", "RELEASE-01",
    "EA-01", "EA-02", "EA-03", "EA-04", "EA-05", "EA-06",
    "REL-01", "REL-02", "REL-03", "REL-04", "REL-05", "REL-06",
    "PLAT-01", "PLAT-02", "PLAT-03", "PLAT-04", "PLAT-05", "PLAT-06", "PLAT-07", "PLAT-08",
    "USB-01", "USB-02", "USB-03", "USB-04",
}
REQUIRED_LABELS = {
    "roadmap", "roadmap:public", "roadmap:internal",
    "agent:queued", "agent:ready", "agent:active", "agent:review", "agent:hold",
}


class SeedError(ValueError):
    """One or more bootstrap-seed invariants were violated."""


@dataclass(frozen=True)
class ValidationResult:
    milestone_count: int
    label_count: int
    item_count: int
    acceptance_coverage: frozenset[str]
    active_task_ids: tuple[str, ...]
    missing_future_packets: tuple[str, ...]


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _unique(values: Iterable[str], noun: str, errors: list[str]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        errors.append(f"duplicate {noun}: {', '.join(sorted(duplicates))}")


def _is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and str(path) == value


def _detect_cycles(items_by_id: dict[str, dict[str, Any]], errors: list[str]) -> None:
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visited:
            return
        if item_id in visiting:
            start = visiting.index(item_id)
            cycle = visiting[start:] + [item_id]
            errors.append("roadmap dependency cycle: " + " -> ".join(cycle))
            return
        visiting.append(item_id)
        for blocker in items_by_id[item_id].get("blockedBy", []):
            if blocker in items_by_id:
                visit(blocker)
        visiting.pop()
        visited.add(item_id)

    for item_id in items_by_id:
        visit(item_id)


def load_seed(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedError(f"could not read roadmap seed {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SeedError("roadmap seed root must be an object")
    return parsed


def validate_seed(seed: dict[str, Any], root: Path) -> ValidationResult:
    errors: list[str] = []

    _require(seed.get("schemaVersion") == SCHEMA_VERSION, f"schemaVersion must be {SCHEMA_VERSION}", errors)
    _require(seed.get("repository") == REPOSITORY, f"repository must be {REPOSITORY}", errors)
    _require(seed.get("bootstrapOnly") is True, "bootstrapOnly must be true", errors)
    _require(seed.get("policy") == REQUIRED_POLICY, "roadmap seed policy does not match the governance contract", errors)

    milestones = seed.get("milestones")
    labels = seed.get("labels")
    items = seed.get("items")
    _require(isinstance(milestones, list) and bool(milestones), "milestones must be a non-empty array", errors)
    _require(isinstance(labels, list) and bool(labels), "labels must be a non-empty array", errors)
    _require(isinstance(items, list) and bool(items), "items must be a non-empty array", errors)
    if not isinstance(milestones, list) or not isinstance(labels, list) or not isinstance(items, list):
        raise SeedError("\n".join(errors))

    milestone_ids: list[str] = []
    milestone_titles: list[str] = []
    milestone_orders: list[int] = []
    milestone_state: dict[str, str] = {}
    for index, milestone in enumerate(milestones):
        if not isinstance(milestone, dict):
            errors.append(f"milestones[{index}] must be an object")
            continue
        mid = milestone.get("id")
        title = milestone.get("title")
        order = milestone.get("order")
        state = milestone.get("state")
        description = milestone.get("description")
        _require(isinstance(mid, str) and bool(mid), f"milestones[{index}].id must be non-empty", errors)
        _require(isinstance(title, str) and bool(title), f"milestones[{index}].title must be non-empty", errors)
        _require(isinstance(order, int) and order >= 0, f"milestones[{index}].order must be a non-negative integer", errors)
        _require(state in {"open", "closed"}, f"milestones[{index}].state must be open or closed", errors)
        _require(isinstance(description, str) and 10 <= len(description) <= 240, f"milestones[{index}].description must be 10–240 characters", errors)
        if isinstance(mid, str):
            milestone_ids.append(mid)
            if isinstance(state, str):
                milestone_state[mid] = state
        if isinstance(title, str):
            milestone_titles.append(title)
        if isinstance(order, int):
            milestone_orders.append(order)
    _unique(milestone_ids, "milestone IDs", errors)
    _unique(milestone_titles, "milestone titles", errors)
    _unique((str(v) for v in milestone_orders), "milestone orders", errors)
    if milestone_orders and sorted(milestone_orders) != list(range(len(milestone_orders))):
        errors.append("milestone order values must be contiguous from 0")
    milestone_order = {
        milestone["id"]: milestone["order"]
        for milestone in milestones
        if isinstance(milestone, dict) and isinstance(milestone.get("id"), str) and isinstance(milestone.get("order"), int)
    }

    label_names: list[str] = []
    for index, label in enumerate(labels):
        if not isinstance(label, dict):
            errors.append(f"labels[{index}] must be an object")
            continue
        name = label.get("name")
        color = label.get("color")
        description = label.get("description")
        _require(isinstance(name, str) and bool(name), f"labels[{index}].name must be non-empty", errors)
        _require(isinstance(color, str) and bool(HEX_RE.fullmatch(color)), f"labels[{index}].color must be six hexadecimal digits", errors)
        _require(isinstance(description, str) and 5 <= len(description) <= 160, f"labels[{index}].description must be 5–160 characters", errors)
        if isinstance(name, str):
            label_names.append(name)
    _unique(label_names, "label names", errors)
    missing_required_labels = REQUIRED_LABELS - set(label_names)
    if missing_required_labels:
        errors.append("missing required labels: " + ", ".join(sorted(missing_required_labels)))

    area_labels = {name.removeprefix("area:") for name in label_names if name.startswith("area:")}
    kind_labels = {name.removeprefix("kind:") for name in label_names if name.startswith("kind:")}

    item_ids: list[str] = []
    items_by_id: dict[str, dict[str, Any]] = {}
    acceptance_coverage: set[str] = set()
    missing_future_packets: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        item_id = item.get("id")
        title = item.get("title")
        summary = item.get("summary")
        milestone = item.get("milestone")
        area = item.get("area")
        kind = item.get("kind")
        visibility = item.get("visibility")
        state = item.get("seedState")
        blockers = item.get("blockedBy")
        gate_ids = item.get("acceptanceIds")
        task_packet = item.get("taskPacket")

        _require(isinstance(item_id, str) and bool(ID_RE.fullmatch(item_id)), f"items[{index}].id must match {ID_RE.pattern}", errors)
        _require(isinstance(title, str) and 8 <= len(title) <= 120, f"{item_id or f'items[{index}]'}.title must be 8–120 characters", errors)
        _require(isinstance(summary, str) and 20 <= len(summary) <= 280, f"{item_id or f'items[{index}]'}.summary must be 20–280 characters", errors)
        _require(milestone in milestone_order, f"{item_id or f'items[{index}]'} references unknown milestone {milestone!r}", errors)
        _require(area in area_labels, f"{item_id or f'items[{index}]'} references unknown area {area!r}", errors)
        _require(kind in kind_labels, f"{item_id or f'items[{index}]'} references unknown kind {kind!r}", errors)
        _require(visibility in REQUIRED_VISIBILITIES, f"{item_id or f'items[{index}]'}.visibility is invalid", errors)
        _require(state in REQUIRED_STATES, f"{item_id or f'items[{index}]'}.seedState is invalid", errors)
        _require(isinstance(blockers, list) and all(isinstance(v, str) for v in blockers), f"{item_id or f'items[{index}]'}.blockedBy must be a string array", errors)
        _require(isinstance(gate_ids, list) and all(isinstance(v, str) and GATE_RE.fullmatch(v) for v in gate_ids), f"{item_id or f'items[{index}]'}.acceptanceIds contains an invalid gate", errors)
        _require(task_packet is None or isinstance(task_packet, str), f"{item_id or f'items[{index}]'}.taskPacket must be a string or null", errors)

        if isinstance(item_id, str):
            item_ids.append(item_id)
            items_by_id[item_id] = item
        if isinstance(gate_ids, list):
            acceptance_coverage.update(v for v in gate_ids if isinstance(v, str) and GATE_RE.fullmatch(v))

        if isinstance(task_packet, str):
            _require(_is_safe_relative_path(task_packet), f"{item_id}.taskPacket must be a safe normalized relative path", errors)
            match = TASK_PACKET_RE.fullmatch(task_packet)
            _require(match is not None, f"{item_id}.taskPacket must match agents/tasks/<ID>/task.md", errors)
            if not (root / task_packet).is_file():
                if state in {"queued", "hold"}:
                    missing_future_packets.append(task_packet)
                else:
                    errors.append(f"{item_id}.taskPacket does not exist: {task_packet}")

    _unique(item_ids, "roadmap item IDs", errors)
    item_id_set = set(item_ids)
    missing_seed_items = REQUIRED_ITEM_IDS - item_id_set
    extra_seed_items = item_id_set - REQUIRED_ITEM_IDS
    if missing_seed_items:
        errors.append("bootstrap seed is missing required items: " + ", ".join(sorted(missing_seed_items)))
    if extra_seed_items:
        errors.append("bootstrap seed has unreviewed extra items: " + ", ".join(sorted(extra_seed_items)))

    for item_id, item in items_by_id.items():
        blockers = item.get("blockedBy", [])
        _unique(blockers, f"blockers for {item_id}", errors)
        for blocker in blockers:
            if blocker == item_id:
                errors.append(f"{item_id} cannot block itself")
            elif blocker not in items_by_id:
                errors.append(f"{item_id} references unknown blocker {blocker}")
            elif item.get("milestone") in milestone_order and items_by_id[blocker].get("milestone") in milestone_order:
                if milestone_order[items_by_id[blocker]["milestone"]] > milestone_order[item["milestone"]]:
                    errors.append(f"{item_id} is blocked by later-milestone item {blocker}")
        if item.get("seedState") in {"ready", "active"}:
            unresolved = [b for b in blockers if items_by_id.get(b, {}).get("seedState") != "done"]
            if unresolved:
                errors.append(f"{item_id} is {item.get('seedState')} but has unfinished seed blocker(s): {', '.join(unresolved)}")
        if item.get("seedState") == "done" and milestone_state.get(item.get("milestone")) != "closed":
            # Closed issues may appear in an open milestone later; the bootstrap uses a
            # dedicated closed foundation milestone and should stay internally clear.
            errors.append(f"done bootstrap item {item_id} must belong to a closed seed milestone")

    _detect_cycles(items_by_id, errors)

    missing_gates = REQUIRED_GATES - acceptance_coverage
    unknown_gates = acceptance_coverage - REQUIRED_GATES
    if missing_gates:
        errors.append("acceptance gates missing roadmap coverage: " + ", ".join(sorted(missing_gates)))
    if unknown_gates:
        errors.append("unknown acceptance gates in roadmap seed: " + ", ".join(sorted(unknown_gates)))

    task_dag_path = root / "agents/task-dag.json"
    try:
        task_dag = json.loads(task_dag_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not read active task DAG: {exc}")
        task_dag = {"tasks": []}
    active_tasks = task_dag.get("tasks", []) if isinstance(task_dag, dict) else []
    active_task_ids: list[str] = []
    for task in active_tasks if isinstance(active_tasks, list) else []:
        if not isinstance(task, dict) or not isinstance(task.get("id"), str):
            errors.append("active task DAG contains a malformed task")
            continue
        task_id = task["id"]
        active_task_ids.append(task_id)
        matches = [
            item_id
            for item_id, item in items_by_id.items()
            if item.get("taskPacket") == f"agents/tasks/{task_id}/task.md"
        ]
        if len(matches) != 1:
            errors.append(f"active task {task_id} must map to exactly one roadmap item; found {len(matches)}")
        elif items_by_id[matches[0]].get("seedState") not in {"ready", "active"}:
            errors.append(f"active task {task_id} maps to {matches[0]} with incompatible seed state {items_by_id[matches[0]].get('seedState')}")

    if errors:
        raise SeedError("roadmap seed validation failed:\n- " + "\n- ".join(errors))

    return ValidationResult(
        milestone_count=len(milestones),
        label_count=len(labels),
        item_count=len(items),
        acceptance_coverage=frozenset(acceptance_coverage),
        active_task_ids=tuple(active_task_ids),
        missing_future_packets=tuple(sorted(set(missing_future_packets))),
    )


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        type=Path,
        default=Path(".github/roadmap/seed.v1.json"),
        help="roadmap seed path, relative to the repository root by default",
    )
    args = parser.parse_args()
    root = repository_root()
    seed_path = args.seed if args.seed.is_absolute() else root / args.seed
    try:
        result = validate_seed(load_seed(seed_path), root)
    except SeedError as exc:
        raise SystemExit(str(exc)) from exc

    print(
        "roadmap seed: PASS "
        f"({result.milestone_count} milestones, {result.label_count} labels, "
        f"{result.item_count} items, {len(result.acceptance_coverage)} acceptance gates)"
    )
    if result.active_task_ids:
        print("active task mapping: " + ", ".join(result.active_task_ids))
    if result.missing_future_packets:
        print(
            "planned task packet paths not created yet: "
            + ", ".join(result.missing_future_packets)
        )


if __name__ == "__main__":
    main()
