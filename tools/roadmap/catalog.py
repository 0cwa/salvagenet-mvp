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
    """Replace fixed first-bootstrap cardinality and milestone filters."""
    if getattr(live_module, "_strategic_catalog_configured", False):
        return

    catalog = roadmap_module.load_seed()
    expected_items = set(roadmap_module.REQUIRED_ITEMS)
    expected_milestone_titles = {
        value["title"] for value in catalog["milestones"]
    }
    expected_milestones = len(expected_milestone_titles)

    def validate_graph(graph: dict[str, Any]) -> None:
        items = graph.get("items")
        milestones = graph.get("milestones")
        if not isinstance(items, dict) or set(items) != expected_items:
            actual = set(items) if isinstance(items, dict) else set()
            raise roadmap_module.RoadmapError(
                "live roadmap item set is incomplete: "
                f"missing={sorted(expected_items-actual)} "
                f"extra={sorted(actual-expected_items)}"
            )
        if not isinstance(milestones, list) or len(milestones) != expected_milestones:
            raise roadmap_module.RoadmapError(
                f"live roadmap must contain the {expected_milestones} reviewed milestone bands"
            )
        milestone_titles = {
            value.get("title") for value in milestones if isinstance(value, dict)
        }
        if milestone_titles != expected_milestone_titles:
            raise roadmap_module.RoadmapError(
                "live roadmap milestone titles differ from the reviewed catalog: "
                f"missing={sorted(expected_milestone_titles-milestone_titles)} "
                f"extra={sorted(milestone_titles-expected_milestone_titles)}"
            )

        for item_id, item in items.items():
            labels = set(item.get("labels", []))
            if "roadmap" not in labels:
                raise roadmap_module.RoadmapError(
                    f"{item_id} is missing roadmap label"
                )
            item["area"] = live_module._one_label(
                labels, "area:", item_id
            ).removeprefix("area:")
            item["kind"] = live_module._one_label(
                labels, "kind:", item_id
            ).removeprefix("kind:")
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
                raise roadmap_module.RoadmapError(
                    f"{item_id} has no reviewed milestone"
                )
            blockers = item.get("blockedBy")
            if not isinstance(blockers, list) or any(
                blocker not in items for blocker in blockers
            ):
                raise roadmap_module.RoadmapError(
                    f"{item_id} has unknown or invalid blockers"
                )
            if len(blockers) != len(set(blockers)):
                raise roadmap_module.RoadmapError(
                    f"{item_id} has duplicate blockers"
                )

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

    def fetch_validated_live_graph(client: Any) -> dict[str, Any]:
        milestones = client.paginate(
            client.repo_path("/milestones?state=all")
        )
        issues = client.paginate(client.repo_path("/issues?state=all"))
        roadmap: dict[str, dict[str, Any]] = {}
        newest: str | None = None

        for issue in issues:
            if "pull_request" in issue:
                continue
            labels = {label["name"] for label in issue.get("labels", [])}
            if "roadmap" not in labels:
                continue
            item_id, task_packet, summary, pull_requests = (
                live_module.parse_issue_body(issue)
            )
            if item_id in roadmap:
                raise roadmap_module.RoadmapError(
                    f"duplicate live roadmap ID {item_id}"
                )
            updated = issue.get("updated_at")
            if isinstance(updated, str) and (
                newest is None or updated > newest
            ):
                newest = updated
            roadmap[item_id] = {
                "id": item_id,
                "number": int(issue["number"]),
                "nodeId": issue.get("node_id"),
                "databaseId": int(issue["id"]),
                "title": live_module.re.sub(
                    r"^\[[A-Z0-9-]+\]\s*", "", issue["title"]
                ),
                "summary": summary,
                "url": issue["html_url"],
                "issueState": issue["state"],
                "labels": sorted(labels),
                "milestoneNumber": issue.get("milestone", {}).get("number")
                if issue.get("milestone")
                else None,
                "milestoneTitle": issue.get("milestone", {}).get("title")
                if issue.get("milestone")
                else None,
                "taskPacket": task_packet,
                "updatedAt": updated,
                "blockedBy": [],
                "pullRequestNumbers": pull_requests,
                "pullRequests": [],
            }

        if set(roadmap) != expected_items:
            raise roadmap_module.RoadmapError(
                "live roadmap item set is incomplete: "
                f"missing={sorted(expected_items-set(roadmap))} "
                f"extra={sorted(set(roadmap)-expected_items)}"
            )

        by_database_id = {
            item["databaseId"]: item_id for item_id, item in roadmap.items()
        }
        for item_id, item in roadmap.items():
            dependencies = client.paginate(
                client.repo_path(
                    f"/issues/{item['number']}/dependencies/blocked_by"
                )
            )
            blockers: list[str] = []
            for dependency in dependencies:
                blocker_id = by_database_id.get(int(dependency["id"]))
                if blocker_id is None:
                    raise roadmap_module.RoadmapError(
                        f"{item_id} is blocked by non-roadmap issue "
                        f"#{dependency.get('number')}"
                    )
                blockers.append(blocker_id)
            item["blockedBy"] = sorted(blockers)
            for number in item["pullRequestNumbers"]:
                pull = client.call(
                    "GET", client.repo_path(f"/pulls/{number}")
                ).value
                item["pullRequests"].append(
                    {
                        "number": number,
                        "state": pull.get("state"),
                        "draft": bool(pull.get("draft")),
                        "merged": pull.get("merged_at") is not None,
                        "mergedAt": pull.get("merged_at"),
                        "url": pull.get("html_url"),
                        "headSha": pull.get("head", {}).get("sha"),
                    }
                )

        milestone_view = [
            {
                "number": int(value["number"]),
                "title": value["title"],
                "state": value["state"],
                "description": value.get("description") or "",
            }
            for value in milestones
            if value.get("title") in expected_milestone_titles
        ]
        graph = {
            "repository": client.repository,
            "newestIssueUpdate": newest,
            "milestones": milestone_view,
            "items": roadmap,
        }
        validate_graph(graph)
        return graph

    live_module.validate_graph = validate_graph
    live_module.fetch_validated_live_graph = fetch_validated_live_graph
    live_module.REQUIRED_ITEMS = expected_items
    live_module._strategic_catalog_configured = True
