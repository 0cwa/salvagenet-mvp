#!/usr/bin/env python3
"""Compose the reviewed bootstrap catalog with later strategic expansions.

The original seed remains immutable provenance for the first live bootstrap. This
module adds reviewed catalog generations without duplicating or rewriting that
history. Existing GitHub issues remain the live planning authority after apply;
the merged catalog supplies completeness, reviewed metadata, and creation input
for newly accepted roadmap items.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPANSION_PATH = ROOT / ".github/roadmap/expansion.v1.json"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _append_unique(values: list[str], additions: list[str]) -> list[str]:
    result = list(values)
    for value in additions:
        if value not in result:
            result.append(value)
    return result


def merge_catalog(base: dict[str, Any], expansion: dict[str, Any]) -> dict[str, Any]:
    if expansion.get("schemaVersion") != 1:
        raise ValueError("roadmap expansion schemaVersion must be 1")
    merged = copy.deepcopy(base)

    milestones = {
        item["id"]: item
        for item in merged.get("milestones", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for item in expansion.get("milestones", []):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("roadmap expansion milestones must be objects with IDs")
        if item["id"] in milestones:
            raise ValueError(f"duplicate roadmap milestone {item['id']}")
        copied = copy.deepcopy(item)
        milestones[item["id"]] = copied
        merged["milestones"].append(copied)

    milestone_order = expansion.get("milestoneOrder")
    if not isinstance(milestone_order, list) or set(milestone_order) != set(milestones):
        raise ValueError("roadmap expansion milestoneOrder must name every merged milestone exactly once")
    for order, milestone_id in enumerate(milestone_order):
        milestones[milestone_id]["order"] = order
    merged["milestones"].sort(key=lambda value: value["order"])

    existing_labels = {
        item.get("name")
        for item in merged.get("labels", [])
        if isinstance(item, dict)
    }
    for label in expansion.get("labels", []):
        if not isinstance(label, dict) or not isinstance(label.get("name"), str):
            raise ValueError("roadmap expansion labels must be objects with names")
        if label["name"] in existing_labels:
            raise ValueError(f"duplicate roadmap label {label['name']}")
        merged["labels"].append(copy.deepcopy(label))
        existing_labels.add(label["name"])

    items = {
        item["id"]: item
        for item in merged.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for item_id, update in expansion.get("itemUpdates", {}).items():
        if item_id not in items:
            raise ValueError(f"roadmap expansion updates unknown item {item_id}")
        if not isinstance(update, dict):
            raise ValueError(f"roadmap expansion update for {item_id} must be an object")
        item = items[item_id]
        item["blockedBy"] = _append_unique(
            list(item.get("blockedBy", [])),
            list(update.get("addBlockedBy", [])),
        )
        item["contextPaths"] = _append_unique(
            list(item.get("contextPaths", [])),
            list(update.get("addContextPaths", [])),
        )

    for item in expansion.get("items", []):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("roadmap expansion items must be objects with IDs")
        if item["id"] in items:
            raise ValueError(f"duplicate roadmap item {item['id']}")
        copied = copy.deepcopy(item)
        items[item["id"]] = copied
        merged["items"].append(copied)

    return merged


def load_expansion(path: Path = EXPANSION_PATH) -> dict[str, Any]:
    return _read_json(path)


def configure_roadmap(roadmap_module: Any) -> None:
    """Teach the existing roadmap engine about the merged reviewed catalog."""
    if getattr(roadmap_module, "_strategic_catalog_configured", False):
        return

    original_load_seed = roadmap_module.load_seed
    expansion = load_expansion()
    preview = merge_catalog(original_load_seed(), expansion)
    all_ids = {item["id"] for item in preview["items"]}

    def load_seed(path: Path = roadmap_module.SEED_PATH) -> dict[str, Any]:
        base = original_load_seed(path)
        if Path(path).resolve() != Path(roadmap_module.SEED_PATH).resolve():
            return base
        return merge_catalog(base, expansion)

    roadmap_module.load_seed = load_seed
    roadmap_module.REQUIRED_ITEMS = all_ids
    roadmap_module.REQUIRED_POST_MVP = set(roadmap_module.REQUIRED_POST_MVP) | set(
        expansion.get("requiredDirections", [])
    )
    roadmap_module.REQUIRED_RELEASE_DEBT = set(roadmap_module.REQUIRED_RELEASE_DEBT) | set(
        expansion.get("releaseBlocking", [])
    )
    roadmap_module._strategic_catalog_configured = True


def configure_live(live_module: Any, roadmap_module: Any) -> None:
    """Replace fixed first-bootstrap cardinality checks with catalog-derived checks."""
    if getattr(live_module, "_strategic_catalog_configured", False):
        return

    expected_items = set(roadmap_module.REQUIRED_ITEMS)
    expected_milestones = len(roadmap_module.load_seed()["milestones"])

    def validate_graph(graph: dict[str, Any]) -> None:
        items = graph.get("items")
        milestones = graph.get("milestones")
        if not isinstance(items, dict) or set(items) != expected_items:
            actual = set(items) if isinstance(items, dict) else set()
            raise roadmap_module.RoadmapError(
                "live roadmap item set is incomplete: "
                f"missing={sorted(expected_items-actual)} extra={sorted(actual-expected_items)}"
            )
        if not isinstance(milestones, list) or len(milestones) != expected_milestones:
            raise roadmap_module.RoadmapError(
                f"live roadmap must contain the {expected_milestones} reviewed milestone bands"
            )
        milestone_titles = {
            value.get("title") for value in milestones if isinstance(value, dict)
        }
        if len(milestone_titles) != expected_milestones or None in milestone_titles:
            raise roadmap_module.RoadmapError(
                "live roadmap milestone titles are missing or duplicated"
            )

        for item_id, item in items.items():
            labels = set(item.get("labels", []))
            if "roadmap" not in labels:
                raise roadmap_module.RoadmapError(f"{item_id} is missing roadmap label")
            item["area"] = live_module._one_label(labels, "area:", item_id).removeprefix("area:")
            item["kind"] = live_module._one_label(labels, "kind:", item_id).removeprefix("kind:")
            visibility = live_module._one_label(labels, "roadmap:", item_id)
            if visibility not in {"roadmap:public", "roadmap:internal"}:
                raise roadmap_module.RoadmapError(
                    f"{item_id} has invalid visibility label {visibility}"
                )
            item["public"] = visibility == "roadmap:public"
            agent_labels = sorted(
                value
                for value in labels
                if value in set(roadmap_module.AGENT_LABELS.values())
            )
            if len(agent_labels) > 1:
                raise roadmap_module.RoadmapError(
                    f"{item_id} has multiple agent-state labels: {agent_labels}"
                )
            if item.get("milestoneTitle") not in milestone_titles:
                raise roadmap_module.RoadmapError(f"{item_id} has no reviewed milestone")
            blockers = item.get("blockedBy")
            if not isinstance(blockers, list) or any(
                blocker not in items for blocker in blockers
            ):
                raise roadmap_module.RoadmapError(
                    f"{item_id} has unknown or invalid blockers"
                )
            if len(blockers) != len(set(blockers)):
                raise roadmap_module.RoadmapError(f"{item_id} has duplicate blockers")

        visiting: list[str] = []
        complete: set[str] = set()

        def visit(item_id: str) -> None:
            if item_id in complete:
                return
            if item_id in visiting:
                cycle = visiting[visiting.index(item_id) :] + [item_id]
                raise roadmap_module.RoadmapError(
                    "live roadmap dependency cycle: " + " -> ".join(cycle)
                )
            visiting.append(item_id)
            for blocker in items[item_id]["blockedBy"]:
                visit(blocker)
            visiting.pop()
            complete.add(item_id)

        for item_id in sorted(items):
            visit(item_id)

    live_module.validate_graph = validate_graph
    live_module.REQUIRED_ITEMS = expected_items
    live_module._strategic_catalog_configured = True
