#!/usr/bin/env python3
"""Strict live GitHub projection for the SalvageNet roadmap.

This module keeps transient GitHub transport failures distinct from structural
roadmap errors. Only transient failures may use a recent complete snapshot.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib import error, request

from roadmap import (
    API_VERSION,
    AGENT_LABELS,
    ApiResult,
    GitHubClient,
    REQUIRED_ITEMS,
    ROADMAP_MARKER_RE,
    RoadmapError,
    TASK_MARKER_RE,
)

PUBLIC_SUMMARY_RE = re.compile(
    r"(?:^|\n)## Public summary\s*\n+(?P<summary>.*?)(?=\n## |\Z)",
    re.DOTALL,
)
PR_REFERENCE_RE = re.compile(r"\bPR\s+#(?P<number>[1-9][0-9]*)\b", re.IGNORECASE)


class RoadmapTransportError(RuntimeError):
    """A bounded transient network, gateway, or rate-limit failure."""


class StrictGitHubClient(GitHubClient):
    """GitHub client that distinguishes transient failures from invalid data/API use."""

    def call(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        *,
        accept: str = "application/vnd.github+json",
        retries: int = 5,
    ) -> ApiResult:
        url = self.api_url + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "salvagenet-roadmap/1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if data is not None:
            headers["Content-Type"] = "application/json"

        last_transient: str | None = None
        for attempt in range(retries):
            req = request.Request(url, data=data, headers=headers, method=method)
            try:
                with request.urlopen(req, timeout=45) as response:
                    raw = response.read()
                    value = json.loads(raw) if raw else None
                    return ApiResult(response.status, {k.lower(): v for k, v in response.headers.items()}, value)
            except error.HTTPError as exc:
                raw = exc.read()
                detail = raw.decode("utf-8", "replace")[:1200]
                remaining = exc.headers.get("x-ratelimit-remaining")
                transient = exc.code in {429, 502, 503, 504} or (exc.code == 403 and remaining == "0")
                if transient:
                    last_transient = f"HTTP {exc.code}: {detail}"
                    if attempt + 1 < retries:
                        retry_after = exc.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 20)
                        time.sleep(delay)
                        continue
                    raise RoadmapTransportError(f"GitHub API {method} {path} remained unavailable: {last_transient}") from exc
                raise RoadmapError(f"GitHub API {method} {path} rejected the request: HTTP {exc.code}: {detail}") from exc
            except error.URLError as exc:
                last_transient = str(exc)
                if attempt + 1 < retries:
                    time.sleep(min(2**attempt, 20))
                    continue
                raise RoadmapTransportError(f"GitHub API {method} {path} remained unavailable: {last_transient}") from exc
        raise RoadmapTransportError(f"GitHub API {method} {path} remained unavailable: {last_transient}")


def parse_issue_body(issue: dict[str, Any]) -> tuple[str, str | None, str, list[int]]:
    body = issue.get("body") or ""
    marker = ROADMAP_MARKER_RE.search(body)
    if not marker:
        raise RoadmapError(f"roadmap-labelled issue #{issue.get('number')} has no stable ID marker")
    task = TASK_MARKER_RE.search(body)
    summary_match = PUBLIC_SUMMARY_RE.search(body)
    if not summary_match:
        raise RoadmapError(f"roadmap issue {marker.group(1)} has no structured Public summary section")
    summary = " ".join(summary_match.group("summary").strip().split())
    if not (20 <= len(summary) <= 320):
        raise RoadmapError(f"roadmap issue {marker.group(1)} public summary must be 20–320 characters")
    pull_requests = sorted({int(match.group("number")) for match in PR_REFERENCE_RE.finditer(body)})
    return (
        marker.group(1),
        task.group(1).strip() if task and task.group(1).strip() else None,
        summary,
        pull_requests,
    )


def _one_label(labels: set[str], prefix: str, item_id: str) -> str:
    values = sorted(value for value in labels if value.startswith(prefix))
    if len(values) != 1:
        raise RoadmapError(f"{item_id} must have exactly one {prefix} label; found {values}")
    return values[0]


def validate_graph(graph: dict[str, Any]) -> None:
    items = graph.get("items")
    milestones = graph.get("milestones")
    if not isinstance(items, dict) or set(items) != REQUIRED_ITEMS:
        actual = set(items) if isinstance(items, dict) else set()
        raise RoadmapError(
            f"live roadmap item set is incomplete: missing={sorted(REQUIRED_ITEMS-actual)} extra={sorted(actual-REQUIRED_ITEMS)}"
        )
    if not isinstance(milestones, list) or len(milestones) != 7:
        raise RoadmapError("live roadmap must contain the seven reviewed milestone bands")
    milestone_titles = {value.get("title") for value in milestones if isinstance(value, dict)}
    if len(milestone_titles) != 7 or None in milestone_titles:
        raise RoadmapError("live roadmap milestone titles are missing or duplicated")

    for item_id, item in items.items():
        labels = set(item.get("labels", []))
        if "roadmap" not in labels:
            raise RoadmapError(f"{item_id} is missing roadmap label")
        item["area"] = _one_label(labels, "area:", item_id).removeprefix("area:")
        item["kind"] = _one_label(labels, "kind:", item_id).removeprefix("kind:")
        visibility = _one_label(labels, "roadmap:", item_id)
        if visibility not in {"roadmap:public", "roadmap:internal"}:
            raise RoadmapError(f"{item_id} has invalid visibility label {visibility}")
        item["public"] = visibility == "roadmap:public"
        agent_labels = sorted(value for value in labels if value in set(AGENT_LABELS.values()))
        if len(agent_labels) > 1:
            raise RoadmapError(f"{item_id} has multiple agent-state labels: {agent_labels}")
        if item.get("milestoneTitle") not in milestone_titles:
            raise RoadmapError(f"{item_id} has no reviewed milestone")
        blockers = item.get("blockedBy")
        if not isinstance(blockers, list) or any(blocker not in items for blocker in blockers):
            raise RoadmapError(f"{item_id} has unknown or invalid blockers")
        if len(blockers) != len(set(blockers)):
            raise RoadmapError(f"{item_id} has duplicate blockers")

    visiting: list[str] = []
    complete: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in complete:
            return
        if item_id in visiting:
            cycle = visiting[visiting.index(item_id) :] + [item_id]
            raise RoadmapError("live roadmap dependency cycle: " + " -> ".join(cycle))
        visiting.append(item_id)
        for blocker in items[item_id]["blockedBy"]:
            visit(blocker)
        visiting.pop()
        complete.add(item_id)

    for item_id in sorted(items):
        visit(item_id)


def fetch_validated_live_graph(client: StrictGitHubClient) -> dict[str, Any]:
    milestones = client.paginate(client.repo_path("/milestones?state=all"))
    issues = client.paginate(client.repo_path("/issues?state=all"))
    roadmap: dict[str, dict[str, Any]] = {}
    newest: str | None = None

    for issue in issues:
        if "pull_request" in issue:
            continue
        labels = {label["name"] for label in issue.get("labels", [])}
        if "roadmap" not in labels:
            continue
        item_id, task_packet, summary, pull_requests = parse_issue_body(issue)
        if item_id in roadmap:
            raise RoadmapError(f"duplicate live roadmap ID {item_id}")
        updated = issue.get("updated_at")
        if isinstance(updated, str) and (newest is None or updated > newest):
            newest = updated
        roadmap[item_id] = {
            "id": item_id,
            "number": int(issue["number"]),
            "nodeId": issue.get("node_id"),
            "databaseId": int(issue["id"]),
            "title": re.sub(r"^\[[A-Z0-9-]+\]\s*", "", issue["title"]),
            "summary": summary,
            "url": issue["html_url"],
            "issueState": issue["state"],
            "labels": sorted(labels),
            "milestoneNumber": issue.get("milestone", {}).get("number") if issue.get("milestone") else None,
            "milestoneTitle": issue.get("milestone", {}).get("title") if issue.get("milestone") else None,
            "taskPacket": task_packet,
            "updatedAt": updated,
            "blockedBy": [],
            "pullRequestNumbers": pull_requests,
            "pullRequests": [],
        }

    if set(roadmap) != REQUIRED_ITEMS:
        raise RoadmapError(
            f"live roadmap item set is incomplete: missing={sorted(REQUIRED_ITEMS-set(roadmap))} extra={sorted(set(roadmap)-REQUIRED_ITEMS)}"
        )

    by_database_id = {item["databaseId"]: item_id for item_id, item in roadmap.items()}
    for item_id, item in roadmap.items():
        dependencies = client.paginate(client.repo_path(f"/issues/{item['number']}/dependencies/blocked_by"))
        blockers: list[str] = []
        for dependency in dependencies:
            blocker_id = by_database_id.get(int(dependency["id"]))
            if blocker_id is None:
                raise RoadmapError(f"{item_id} is blocked by non-roadmap issue #{dependency.get('number')}")
            blockers.append(blocker_id)
        item["blockedBy"] = sorted(blockers)
        for number in item["pullRequestNumbers"]:
            pull = client.call("GET", client.repo_path(f"/pulls/{number}")).value
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
        if value["title"].startswith(("M0", "M1", "M2", "M3", "M4", "MVP+"))
    ]
    graph = {
        "repository": client.repository,
        "newestIssueUpdate": newest,
        "milestones": milestone_view,
        "items": roadmap,
    }
    validate_graph(graph)
    return graph
