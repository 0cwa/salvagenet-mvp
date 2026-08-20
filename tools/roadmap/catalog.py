#!/usr/bin/env python3
"""Compose reviewed roadmap generations and live milestone migrations.

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
MILESTONE_UPDATES_PATH = ROOT / ".github/roadmap/milestone-updates.v1.json"


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


def load_expansion(path: Path = EXPANSION_PATH) -> dict[str, Any]:
    return _read_json(path)


def load_milestone_updates(
    path: Path = MILESTONE_UPDATES_PATH,
) -> dict[str, Any]:
    return _read_json(path)


def _validated_milestone_updates(value: dict[str, Any]) -> list[dict[str, Any]]:
    if value.get("schemaVersion") != 1:
        raise ValueError("milestone update schemaVersion must be 1")
    updates = value.get("updates")
    if not isinstance(updates, list):
        raise ValueError("milestone updates must be an array")
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, update in enumerate(updates):
        if not isinstance(update, dict):
            raise ValueError(f"milestone updates[{index}] must be an object")
        milestone_id = update.get("id")
        title = update.get("title")
        description = update.get("description")
        state = update.get("state")
        aliases = update.get("fromTitles")
        if not isinstance(milestone_id, str) or not milestone_id:
            raise ValueError(f"milestone updates[{index}].id must be non-empty")
        if milestone_id in seen:
            raise ValueError(f"duplicate milestone update {milestone_id}")
        if not isinstance(title, str) or not 5 <= len(title) <= 120:
            raise ValueError(f"milestone update {milestone_id} has invalid title")
        if not isinstance(description, str) or not 10 <= len(description) <= 240:
            raise ValueError(
                f"milestone update {milestone_id} has invalid description"
            )
        if state not in {"open", "closed"}:
            raise ValueError(f"milestone update {milestone_id} has invalid state")
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) and alias for alias in aliases
        ):
            raise ValueError(
                f"milestone update {milestone_id}.fromTitles must be a string array"
            )
        if title in aliases or len(aliases) != len(set(aliases)):
            raise ValueError(
                f"milestone update {milestone_id} has duplicate/current title aliases"
            )
        seen.add(milestone_id)
        result.append(copy.deepcopy(update))
    return result


def merge_catalog(
    base: dict[str, Any],
    expansion: dict[str, Any],
    milestone_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if expansion.get("schemaVersion") != 1:
        raise ValueError("roadmap expansion schemaVersion must be 1")
    merged = copy.deepcopy(base)

    milestones = {
        item["id"]: item
        for item in merged.get("milestones", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for update in _validated_milestone_updates(
        milestone_updates or {"schemaVersion": 1, "updates": []}
    ):
        milestone_id = update["id"]
        if milestone_id not in milestones:
            raise ValueError(
                f"milestone update references unknown milestone {milestone_id}"
            )
        milestone = milestones[milestone_id]
        previous = _append_unique(
            list(milestone.get("previousTitles", [])),
            [milestone["title"], *update["fromTitles"]],
        )
        milestone["previousTitles"] = [
            value for value in previous if value != update["title"]
        ]
        milestone["title"] = update["title"]
        milestone["description"] = update["description"]
        milestone["state"] = update["state"]

    for item in expansion.get("milestones", []):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("roadmap expansion milestones must be objects with IDs")
        if item["id"] in milestones:
            raise ValueError(f"duplicate roadmap milestone {item['id']}")
        copied = copy.deepcopy(item)
        milestones[item["id"]] = copied
        merged["milestones"].append(copied)

    milestone_order = expansion.get("milestoneOrder")
    if not isinstance(milestone_order, list) or set(milestone_order) != set(
        milestones
    ):
        raise ValueError(
            "roadmap expansion milestoneOrder must name every merged milestone exactly once"
        )
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
            raise ValueError(
                f"roadmap expansion update for {item_id} must be an object"
            )
        unknown = set(update) - {"addBlockedBy", "addContextPaths"}
        if unknown:
            raise ValueError(
                f"roadmap expansion update for {item_id} has unknown keys: "
                f"{sorted(unknown)}"
            )
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


class _MilestonePreviewClient:
    """Delegate GitHub calls while previewing reviewed milestone mutations."""

    def __init__(
        self,
        delegate: Any,
        preview_by_number: dict[int, dict[str, Any]],
    ) -> None:
        self._delegate = delegate
        self._preview_by_number = preview_by_number
        self.repository = delegate.repository

    def repo_path(self, suffix: str) -> str:
        return self._delegate.repo_path(suffix)

    def call(self, *args: Any, **kwargs: Any) -> Any:
        return self._delegate.call(*args, **kwargs)

    def paginate(self, path: str) -> list[dict[str, Any]]:
        values = self._delegate.paginate(path)
        if "/milestones?state=all" not in path:
            return values
        return [
            copy.deepcopy(self._preview_by_number.get(int(value["number"]), value))
            for value in values
        ]


def prepare_live_milestone_updates(
    client: Any,
    milestone_updates: dict[str, Any],
    *,
    apply: bool,
    roadmap_module: Any,
) -> tuple[Any, list[str]]:
    """Rename/update existing milestones before ordinary catalog bootstrap.

    GitHub milestone assignments survive an in-place rename. During dry-run the
    returned client previews those mutations so the ordinary bootstrap does not
    incorrectly propose a duplicate milestone.
    """
    updates = _validated_milestone_updates(milestone_updates)
    live_values = client.paginate(client.repo_path("/milestones?state=all"))
    by_title = {value["title"]: value for value in live_values}
    preview_by_number: dict[int, dict[str, Any]] = {}
    plan: list[str] = []

    for update in updates:
        desired = by_title.get(update["title"])
        aliases = [
            by_title[title]
            for title in update["fromTitles"]
            if title in by_title
        ]
        if desired is not None and aliases:
            raise roadmap_module.RoadmapError(
                f"milestone update {update['id']} found both current and previous titles"
            )
        if len(aliases) > 1:
            raise roadmap_module.RoadmapError(
                f"milestone update {update['id']} matched multiple previous titles"
            )
        live = desired or (aliases[0] if aliases else None)
        if live is None:
            # A fresh repository has nothing to migrate. Ordinary bootstrap will
            # create the milestone under its reviewed current title.
            continue

        changed = (
            live.get("title") != update["title"]
            or (live.get("description") or "") != update["description"]
            or live.get("state") != update["state"]
        )
        if not changed:
            continue

        verb = "rename" if live.get("title") != update["title"] else "update"
        plan.append(
            f"{verb} milestone {live.get('title')} -> {update['title']}"
        )
        replacement = copy.deepcopy(live)
        replacement.update(
            {
                "title": update["title"],
                "description": update["description"],
                "state": update["state"],
            }
        )
        preview_by_number[int(live["number"])] = replacement
        if apply:
            client.call(
                "PATCH",
                client.repo_path(f"/milestones/{int(live['number'])}"),
                {
                    "title": update["title"],
                    "description": update["description"],
                    "state": update["state"],
                },
            )

    if apply or not preview_by_number:
        return client, plan
    return _MilestonePreviewClient(client, preview_by_number), plan


def configure_roadmap(roadmap_module: Any) -> None:
    """Teach the existing roadmap engine about the merged reviewed catalog."""
    if getattr(roadmap_module, "_strategic_catalog_configured", False):
        return

    original_load_seed = roadmap_module.load_seed
    expansion = load_expansion()
    milestone_updates = load_milestone_updates()
    preview = merge_catalog(
        original_load_seed(), expansion, milestone_updates
    )
    all_ids = {item["id"] for item in preview["items"]}

    def load_seed(path: Path = roadmap_module.SEED_PATH) -> dict[str, Any]:
        base = original_load_seed(path)
        if Path(path).resolve() != Path(roadmap_module.SEED_PATH).resolve():
            return base
        return merge_catalog(base, expansion, milestone_updates)

    roadmap_module.load_seed = load_seed
    roadmap_module.REQUIRED_ITEMS = all_ids
    roadmap_module.REQUIRED_POST_MVP = set(
        roadmap_module.REQUIRED_POST_MVP
    ) | set(expansion.get("requiredDirections", []))
    roadmap_module.REQUIRED_RELEASE_DEBT = set(
        roadmap_module.REQUIRED_RELEASE_DEBT
    ) | set(expansion.get("releaseBlocking", []))
    roadmap_module._strategic_catalog_configured = True


def configure_live(live_module: Any, roadmap_module: Any) -> None:
    """Configure the single live validator for the composed catalog."""
    if getattr(live_module, "_strategic_catalog_configured", False):
        return
    if not getattr(roadmap_module, "_strategic_catalog_configured", False):
        raise ValueError("configure_roadmap must run before configure_live")

    catalog = roadmap_module.load_seed()
    live_module.REQUIRED_ITEMS = set(roadmap_module.REQUIRED_ITEMS)
    live_module.EXPECTED_MILESTONE_TITLES = {
        value["title"] for value in catalog["milestones"]
    }
    live_module._strategic_catalog_configured = True
