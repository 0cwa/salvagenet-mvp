#!/usr/bin/env python3
"""Validate the reviewed bootstrap seed for the SalvageNet issue roadmap.

The seed is bootstrap input, not a permanent second roadmap. Before GitHub
Issues become authoritative it must cover current acceptance and post-MVP
directions and form a complete acyclic dependency graph.

The seed is deliberately *not* compared with the current active task DAG. After
bootstrap it remains historical while task authorization continues to change.
Steady-state roadmap tooling is responsible for reconciling live issues with the
current DAG.
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

REQUIRED_GATES = {
    *(f"B{i:02d}" for i in range(1, 21)),
    *(f"U{i:02d}" for i in range(1, 5)),
}
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
    "PLAT-01", "PLAT-02", "PLAT-03", "PLAT-04", "PLAT-05", "PLAT-06", "PLAT-07",
    "PLAT-08", "PLAT-09", "PLAT-10", "PLAT-11", "PLAT-12", "PLAT-13", "PLAT-14",
    "USB-01", "USB-02", "USB-03", "USB-04", "USB-05",
}
REQUIRED_LABELS = {
    "roadmap", "roadmap:public", "roadmap:internal",
    "agent:queued", "agent:ready", "agent:active", "agent:review", "agent:hold",
}
REQUIRED_POST_MVP_IDS = {
    "PLAT-01", "PLAT-03", "PLAT-04", "PLAT-05", "PLAT-06", "PLAT-07", "PLAT-08",
    "PLAT-09", "PLAT-10", "PLAT-11", "PLAT-12", "PLAT-13", "PLAT-14", "USB-05",
}


class SeedError(ValueError):
    """One or more bootstrap-seed invariants were violated."""


@dataclass(frozen=True)
class ValidationResult:
    milestone_count: int
    label_count: int
    item_count: int
    acceptance_coverage: frozenset[str]
    seed_active_item_ids: tuple[str, ...]
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


def _safe_relative_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and str(path) == value


def _detect_cycles(items: dict[str, dict[str, Any]], errors: list[str]) -> None:
    done: set[str] = set()
    stack: list[str] = []

    def visit(item_id: str) -> None:
        if item_id in done:
            return
        if item_id in stack:
            cycle = stack[stack.index(item_id):] + [item_id]
            errors.append("roadmap dependency cycle: " + " -> ".join(cycle))
            return
        stack.append(item_id)
        for blocker in items[item_id].get("blockedBy", []):
            if blocker in items:
                visit(blocker)
        stack.pop()
        done.add(item_id)

    for item_id in items:
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
    _require(seed.get("policy") == REQUIRED_POLICY, "roadmap seed policy differs from governance", errors)

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
    milestone_order: dict[str, int] = {}
    for index, milestone in enumerate(milestones):
        if not isinstance(milestone, dict):
            errors.append(f"milestones[{index}] must be an object")
            continue
        mid, title = milestone.get("id"), milestone.get("title")
        order, state = milestone.get("order"), milestone.get("state")
        description = milestone.get("description")
        _require(isinstance(mid, str) and bool(mid), f"milestones[{index}].id must be non-empty", errors)
        _require(isinstance(title, str) and bool(title), f"milestones[{index}].title must be non-empty", errors)
        _require(isinstance(order, int) and order >= 0, f"milestones[{index}].order must be non-negative", errors)
        _require(state in {"open", "closed"}, f"milestones[{index}].state must be open or closed", errors)
        _require(isinstance(description, str) and 10 <= len(description) <= 240,
                 f"milestones[{index}].description must be 10–240 characters", errors)
        if isinstance(mid, str):
            milestone_ids.append(mid)
            if isinstance(order, int):
                milestone_order[mid] = order
        if isinstance(title, str):
            milestone_titles.append(title)
        if isinstance(order, int):
            milestone_orders.append(order)
    _unique(milestone_ids, "milestone IDs", errors)
    _unique(milestone_titles, "milestone titles", errors)
    _unique((str(value) for value in milestone_orders), "milestone orders", errors)
    if milestone_orders and sorted(milestone_orders) != list(range(len(milestone_orders))):
        errors.append("milestone order values must be contiguous from 0")

    label_names: list[str] = []
    for index, label in enumerate(labels):
        if not isinstance(label, dict):
            errors.append(f"labels[{index}] must be an object")
            continue
        name, color, description = label.get("name"), label.get("color"), label.get("description")
        _require(isinstance(name, str) and bool(name), f"labels[{index}].name must be non-empty", errors)
        _require(isinstance(color, str) and bool(HEX_RE.fullmatch(color)),
                 f"labels[{index}].color must be six hexadecimal digits", errors)
        _require(isinstance(description, str) and 5 <= len(description) <= 160,
                 f"labels[{index}].description must be 5–160 characters", errors)
        if isinstance(name, str):
            label_names.append(name)
    _unique(label_names, "label names", errors)
    missing_labels = REQUIRED_LABELS - set(label_names)
    if missing_labels:
        errors.append("missing required labels: " + ", ".join(sorted(missing_labels)))
    areas = {name.removeprefix("area:") for name in label_names if name.startswith("area:")}
    kinds = {name.removeprefix("kind:") for name in label_names if name.startswith("kind:")}

    item_ids: list[str] = []
    items_by_id: dict[str, dict[str, Any]] = {}
    coverage: set[str] = set()
    seed_active_ids: list[str] = []
    missing_future_packets: list[str] = []

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        item_id = item.get("id")
        title, summary = item.get("title"), item.get("summary")
        milestone, area, kind = item.get("milestone"), item.get("area"), item.get("kind")
        visibility, state = item.get("visibility"), item.get("seedState")
        blockers, gate_ids, task_packet = item.get("blockedBy"), item.get("acceptanceIds"), item.get("taskPacket")
        name = item_id if isinstance(item_id, str) else f"items[{index}]"

        _require(isinstance(item_id, str) and bool(ID_RE.fullmatch(item_id)), f"{name}.id is invalid", errors)
        _require(isinstance(title, str) and 8 <= len(title) <= 120, f"{name}.title must be 8–120 characters", errors)
        _require(isinstance(summary, str) and 20 <= len(summary) <= 280, f"{name}.summary must be 20–280 characters", errors)
        _require(milestone in milestone_order, f"{name} references unknown milestone {milestone!r}", errors)
        _require(area in areas, f"{name} references unknown area {area!r}", errors)
        _require(kind in kinds, f"{name} references unknown kind {kind!r}", errors)
        _require(visibility in REQUIRED_VISIBILITIES, f"{name}.visibility is invalid", errors)
        _require(state in REQUIRED_STATES, f"{name}.seedState is invalid", errors)
        _require(isinstance(blockers, list) and all(isinstance(value, str) for value in blockers),
                 f"{name}.blockedBy must be a string array", errors)
        _require(isinstance(gate_ids, list) and all(isinstance(value, str) and GATE_RE.fullmatch(value) for value in gate_ids),
                 f"{name}.acceptanceIds contains an invalid gate", errors)
        _require(task_packet is None or isinstance(task_packet, str), f"{name}.taskPacket must be a string or null", errors)

        if isinstance(item_id, str):
            item_ids.append(item_id)
            items_by_id[item_id] = item
            if state == "active":
                seed_active_ids.append(item_id)
        if isinstance(gate_ids, list):
            coverage.update(value for value in gate_ids if isinstance(value, str) and GATE_RE.fullmatch(value))
        if isinstance(task_packet, str):
            _require(_safe_relative_path(task_packet), f"{name}.taskPacket must be a safe relative path", errors)
            _require(TASK_PACKET_RE.fullmatch(task_packet) is not None,
                     f"{name}.taskPacket must match agents/tasks/<ID>/task.md", errors)
            if not (root / task_packet).is_file():
                if state in {"queued", "hold"}:
                    missing_future_packets.append(task_packet)
                else:
                    errors.append(f"{name}.taskPacket does not exist: {task_packet}")
        elif state == "active":
            errors.append(f"{name} is active in the bootstrap seed but has no task packet")

    _unique(item_ids, "roadmap item IDs", errors)
    actual_ids = set(item_ids)
    missing_items = REQUIRED_ITEM_IDS - actual_ids
    extra_items = actual_ids - REQUIRED_ITEM_IDS
    if missing_items:
        errors.append("bootstrap seed is missing required items: " + ", ".join(sorted(missing_items)))
    if extra_items:
        errors.append("bootstrap seed has unreviewed extra items: " + ", ".join(sorted(extra_items)))
    if not REQUIRED_POST_MVP_IDS <= actual_ids:
        errors.append("bootstrap seed does not cover every accepted post-MVP direction")
    if len(seed_active_ids) > 1:
        errors.append("bootstrap seed may name at most one initially active roadmap item")

    for item_id, item in items_by_id.items():
        blockers = item.get("blockedBy", [])
        _unique(blockers, f"blockers for {item_id}", errors)
        for blocker in blockers:
            if blocker == item_id:
                errors.append(f"{item_id} cannot block itself")
            elif blocker not in items_by_id:
                errors.append(f"{item_id} references unknown blocker {blocker}")
            elif (item.get("milestone") in milestone_order and
                  items_by_id[blocker].get("milestone") in milestone_order and
                  milestone_order[items_by_id[blocker]["milestone"]] > milestone_order[item["milestone"]]):
                errors.append(f"{item_id} is blocked by later-milestone item {blocker}")
        if item.get("seedState") in {"ready", "active"}:
            unresolved = [blocker for blocker in blockers if items_by_id.get(blocker, {}).get("seedState") != "done"]
            if unresolved:
                errors.append(f"{item_id} is {item.get('seedState')} but has unfinished seed blockers: {', '.join(unresolved)}")

    _detect_cycles(items_by_id, errors)
    missing_gates = REQUIRED_GATES - coverage
    unknown_gates = coverage - REQUIRED_GATES
    if missing_gates:
        errors.append("acceptance gates missing roadmap coverage: " + ", ".join(sorted(missing_gates)))
    if unknown_gates:
        errors.append("unknown acceptance gates in roadmap seed: " + ", ".join(sorted(unknown_gates)))

    if errors:
        raise SeedError("roadmap seed validation failed:\n- " + "\n- ".join(errors))

    return ValidationResult(
        milestone_count=len(milestones),
        label_count=len(labels),
        item_count=len(items),
        acceptance_coverage=frozenset(coverage),
        seed_active_item_ids=tuple(seed_active_ids),
        missing_future_packets=tuple(sorted(set(missing_future_packets))),
    )


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=Path(".github/roadmap/seed.v1.json"))
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
    if result.seed_active_item_ids:
        print("initial active seed item: " + ", ".join(result.seed_active_item_ids))
    if result.missing_future_packets:
        print("planned task packet paths not created yet: " + ", ".join(result.missing_future_packets))


if __name__ == "__main__":
    main()
