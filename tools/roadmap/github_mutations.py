#!/usr/bin/env python3
"""Small, bounded GitHub mutation adapter used only by explicit apply."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

try:
    from .common import RoadmapError, issue_body
except ImportError:  # direct import from the explicit apply boundary
    from common import RoadmapError, issue_body


class GitHubMutationClient:
    def __init__(self, repository: str, token: str):
        if "/" not in repository or not token:
            raise RoadmapError("invalid repository or empty GitHub credential")
        self.repository = repository
        self.token = token
        self.base = f"https://api.github.com/repos/{repository}"

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base + path,
            data=body,
            method=method,
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.token}", "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            # Never expose response bodies: they may include issue content or
            # server details. The status is enough for a human to investigate.
            raise RoadmapError(f"GitHub {method} {path} failed with HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RoadmapError(f"GitHub {method} {path} failed: {exc.reason}") from exc

    def apply_seed(self, seed: dict[str, Any]) -> None:
        """Create/verify objects and dependency edges, preserving refinements."""
        labels = {label["name"]: label for label in self.request("GET", "/labels?per_page=100")}
        for label in seed["labels"]:
            if label["name"] not in labels:
                self.request("POST", "/labels", {"name": label["name"], "color": label["color"], "description": label["description"]})
        milestones = {item["title"]: item for item in self.request("GET", "/milestones?state=all&per_page=100")}
        for milestone in seed["milestones"]:
            if milestone["title"] not in milestones:
                self.request("POST", "/milestones", {"title": milestone["title"], "description": milestone["description"]})
        milestones = {item["title"]: item for item in self.request("GET", "/milestones?state=all&per_page=100")}
        issues = self.request("GET", "/issues?state=all&labels=roadmap&per_page=100")
        by_id = {}
        for item in issues:
            body = item.get("body") or ""
            stable_id = next((entry["id"] for entry in seed["issues"] if f"<!-- roadmap-id: {entry['id']} -->" in body), None)
            if stable_id:
                by_id[stable_id] = item
        for issue in seed["issues"]:
            if issue["id"] in by_id:
                continue
            milestone = milestones.get(issue["milestone"])
            if milestone is None:
                raise RoadmapError(f"milestone missing after creation: {issue['milestone']}")
            self.request("POST", "/issues", {"title": f"[{issue['id']}] {issue['title']}", "body": issue_body(issue), "labels": issue["labels"], "milestone": milestone["number"]})
        # GitHub's dependency endpoint is deliberately isolated here. If the
        # server rejects it, apply fails rather than publishing a graph that
        # falsely shows blocked work as ready.
        refreshed = self.request("GET", "/issues?state=all&labels=roadmap&per_page=100")
        by_id = {}
        for item in refreshed:
            body = item.get("body") or ""
            for issue in seed["issues"]:
                if f"<!-- roadmap-id: {issue['id']} -->" in body:
                    by_id[issue["id"]] = item
        for issue in seed["issues"]:
            for dependency in issue["dependencies"]:
                if dependency not in by_id or issue["id"] not in by_id:
                    raise RoadmapError(f"cannot resolve dependency edge {issue['id']} <- {dependency}")
                self.request("POST", f"/issues/{by_id[issue['id']]['number']}/dependencies/blocked_by", {"issue_id": by_id[dependency]["id"]})
