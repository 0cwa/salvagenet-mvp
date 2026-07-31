#!/usr/bin/env python3
"""Synchronize GitHub's active roadmap label with task-dag authorization.

GitHub issues own planned outcomes and ordering. The task DAG owns the much
narrower question of what an agent may implement now. This tool makes that
relationship mechanical without overwriting queued/ready/review/hold planning
state on unrelated issues.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

import roadmap
from catalog import configure_roadmap

configure_roadmap(roadmap)

AGENT_LABELS = set(roadmap.AGENT_LABELS.values())
ACTIVE_LABEL = roadmap.AGENT_LABELS["active"]
STATUS_LABELS = {
    "PLANNED": roadmap.AGENT_LABELS["queued"],
    "QUEUED": roadmap.AGENT_LABELS["queued"],
    "QUEUED_REVIEW": roadmap.AGENT_LABELS["queued"],
    "READY": roadmap.AGENT_LABELS["ready"],
    "REVIEW": roadmap.AGENT_LABELS["review"],
    "IN_REVIEW": roadmap.AGENT_LABELS["review"],
    "HOLD": roadmap.AGENT_LABELS["hold"],
    "PAUSED": roadmap.AGENT_LABELS["hold"],
}


def _task_id(packet: str | None) -> str | None:
    if not packet:
        return None
    return Path(packet).parent.name


def _registry_statuses() -> dict[str, str]:
    registry = roadmap.read_json(roadmap.REGISTRY_PATH)
    result: dict[str, str] = {}
    for item in registry.get("tasks", []):
        if not isinstance(item, dict):
            continue
        task_id = item.get("id")
        status = item.get("status")
        if isinstance(task_id, str) and isinstance(status, str):
            result[task_id] = status.upper()
    for task_id, status in registry.get("cycleStatus", {}).items():
        if isinstance(task_id, str) and isinstance(status, str):
            result.setdefault(task_id, status.upper())
    return result


def desired_agent_label(
    *,
    task_id: str | None,
    active_task_ids: set[str],
    current_agent_labels: set[str],
    issue_open: bool,
    registry_statuses: dict[str, str],
) -> str | None:
    """Return the one desired agent-state label for a roadmap issue."""
    if task_id in active_task_ids:
        return ACTIVE_LABEL

    non_active = current_agent_labels - {ACTIVE_LABEL}
    if len(non_active) > 1:
        raise roadmap.RoadmapError(
            f"issue has multiple non-active agent-state labels: {sorted(non_active)}"
        )
    if non_active:
        return next(iter(non_active))

    if not issue_open:
        return None

    status = registry_statuses.get(task_id or "")
    if status in {"MERGED", "DONE", "SUPERSEDED", "CANCELLED"}:
        return None
    if status in STATUS_LABELS:
        return STATUS_LABELS[status]

    # An open task-bound issue that just left the DAG should never remain
    # active. Queued is the conservative non-authorizing fallback until a
    # reviewed phase transition assigns a more specific planning state.
    return roadmap.AGENT_LABELS["queued"] if task_id else None


def reconcile_label_names(
    labels: list[str],
    desired_agent: str | None,
) -> list[str]:
    preserved = [value for value in labels if value not in AGENT_LABELS]
    if desired_agent:
        preserved.append(desired_agent)
    return sorted(set(preserved))


def synchronize(client: roadmap.GitHubClient, *, apply: bool) -> dict[str, Any]:
    dag = roadmap.read_json(roadmap.DAG_PATH)
    active_task_ids = {
        item["id"]
        for item in dag.get("tasks", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    registry_statuses = _registry_statuses()

    issues = client.paginate(client.repo_path("/issues?state=all"))
    task_issues: dict[str, dict[str, Any]] = {}
    roadmap_issues: list[dict[str, Any]] = []

    for issue in issues:
        if "pull_request" in issue:
            continue
        labels = [value["name"] for value in issue.get("labels", [])]
        if "roadmap" not in labels:
            continue
        body = issue.get("body") or ""
        marker = roadmap.ROADMAP_MARKER_RE.search(body)
        if not marker:
            raise roadmap.RoadmapError(
                f"roadmap-labelled issue #{issue.get('number')} has no stable ID marker"
            )
        packet_match = roadmap.TASK_MARKER_RE.search(body)
        packet = packet_match.group(1).strip() if packet_match else ""
        task_id = _task_id(packet or None)
        normalized = {
            "id": marker.group(1),
            "number": int(issue["number"]),
            "state": issue.get("state"),
            "labels": labels,
            "taskId": task_id,
        }
        roadmap_issues.append(normalized)
        if task_id:
            if task_id in task_issues:
                raise roadmap.RoadmapError(
                    f"task {task_id} is bound to multiple roadmap issues"
                )
            task_issues[task_id] = normalized

    missing_active = active_task_ids - set(task_issues)
    if missing_active:
        raise roadmap.RoadmapError(
            f"active DAG tasks have no live roadmap issue: {sorted(missing_active)}"
        )

    closed_active = sorted(
        task_id
        for task_id in active_task_ids
        if task_issues[task_id]["state"] != "open"
    )
    if closed_active:
        raise roadmap.RoadmapError(
            f"active DAG tasks are bound to closed issues: {closed_active}"
        )

    changes: list[dict[str, Any]] = []
    for issue in roadmap_issues:
        current_agent = set(issue["labels"]) & AGENT_LABELS
        desired = desired_agent_label(
            task_id=issue["taskId"],
            active_task_ids=active_task_ids,
            current_agent_labels=current_agent,
            issue_open=issue["state"] == "open",
            registry_statuses=registry_statuses,
        )
        desired_set = {desired} if desired else set()
        if current_agent == desired_set:
            continue
        new_labels = reconcile_label_names(issue["labels"], desired)
        change = {
            "roadmapId": issue["id"],
            "issue": issue["number"],
            "taskId": issue["taskId"],
            "before": sorted(current_agent),
            "after": sorted(desired_set),
        }
        changes.append(change)
        if apply:
            client.call(
                "PATCH",
                client.repo_path(f"/issues/{issue['number']}"),
                {"labels": new_labels},
            )

    return {
        "mode": "apply" if apply else "check",
        "activeTasks": sorted(active_task_ids),
        "changes": changes,
        "inSync": not changes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise roadmap.RoadmapError(
            "GH_TOKEN or GITHUB_TOKEN is required for live authorization synchronization"
        )
    seed = roadmap.load_seed()
    result = synchronize(
        roadmap.GitHubClient(seed["repository"], token),
        apply=args.apply,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not args.apply and not result["inSync"]:
        raise roadmap.RoadmapError(
            "GitHub roadmap agent-state labels differ from task-dag authorization"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except roadmap.RoadmapError as exc:
        print(f"roadmap authorization error: {exc}", file=sys.stderr)
        raise SystemExit(2)
