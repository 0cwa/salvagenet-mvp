#!/usr/bin/env python3
"""Synchronize a bounded roadmap graph and publish generated views.

Offline seed/fixture mode is the normal development path. ``--live`` is a
read-only GitHub fetch boundary; it never creates, edits, closes, or labels an
issue. Mutation belongs exclusively to the explicit bootstrap apply path.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    from .common import CACHE_PATH, FRESHNESS_HOURS, INDEX_PATH, MAX_ISSUES, ROOT, SEED_PATH, SNAPSHOT_PATH, RoadmapError, graph_from_seed, index_from_graph, load_json, load_seed, parse_time, select_fallback_snapshot, snapshot_from_graph, snapshot_freshness, source_hash, write_json
except ImportError:  # direct script execution from Makefile/CI
    from common import CACHE_PATH, FRESHNESS_HOURS, INDEX_PATH, MAX_ISSUES, ROOT, SEED_PATH, SNAPSHOT_PATH, RoadmapError, graph_from_seed, index_from_graph, load_json, load_seed, parse_time, select_fallback_snapshot, snapshot_from_graph, snapshot_freshness, source_hash, write_json


def bounded_request(url: str, token: str | None = None) -> Any:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        status = getattr(exc, "code", "network")
        raise RoadmapError(f"bounded live fetch failed ({status})") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RoadmapError("bounded live fetch returned invalid JSON") from exc
    return value


def fetch_live(seed: dict[str, Any]) -> dict[str, Any]:
    """Fetch only roadmap issue metadata; comments and history are excluded."""
    repository = seed["repository"]
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    issue_records: list[dict[str, Any]] = []
    for page in range(1, 4):
        query = urllib.parse.urlencode({"state": "all", "labels": "roadmap", "per_page": 100, "page": page})
        value = bounded_request(f"https://api.github.com/repos/{repository}/issues?{query}", token)
        if not isinstance(value, list):
            raise RoadmapError("live issue response is not a list")
        issue_records.extend(value)
        if len(issue_records) > MAX_ISSUES:
            raise RoadmapError(f"live issue graph exceeds {MAX_ISSUES} issues")
        if len(value) < 100:
            break
    if len(issue_records) >= 300:
        raise RoadmapError("live issue pagination is unbounded")

    seed_by_id = {issue["id"]: issue for issue in seed["issues"]}
    live_by_id: dict[str, dict[str, Any]] = {}
    for record in issue_records:
        body = record.get("body") or ""
        stable_id = next((stable_id for stable_id in seed_by_id if f"<!-- roadmap-id: {stable_id} -->" in body), None)
        if stable_id is None:
            # Unnormalized proposals are deliberately ignored, not published.
            continue
        if stable_id in live_by_id:
            raise RoadmapError(f"duplicate live stable ID: {stable_id}")
        labels = [label.get("name") for label in record.get("labels", []) if isinstance(label, dict)]
        live_by_id[stable_id] = {
            "number": record.get("number"), "title": record.get("title"), "url": record.get("html_url"),
            "state": "done" if record.get("state") == "closed" else "open",
            "updatedAt": record.get("updated_at"), "milestone": (record.get("milestone") or {}).get("title"),
            "labels": labels,
        }
    if not live_by_id:
        # The first bootstrap is expected to see no normalized roadmap issues.
        return {"schemaVersion": 1, "issues": []}
    if set(live_by_id) != set(seed_by_id):
        missing = sorted(set(seed_by_id) - set(live_by_id))
        raise RoadmapError(f"live graph is incomplete; missing stable IDs: {', '.join(missing[:10])}")

    # Start from the reviewed metadata contract, then overlay only fields
    # GitHub owns. Full bodies are not persisted and comments are never read.
    live_seed = json.loads(json.dumps(seed))
    for issue in live_seed["issues"]:
        live = live_by_id[issue["id"]]
        issue["issueNumber"] = live["number"]
        issue["title"] = live["title"].removeprefix(f"[{issue['id']}] ")
        issue["seedState"] = "done" if live["state"] == "done" else issue["seedState"]
        issue["reviewedAt"] = live["updatedAt"]
        if live["milestone"] and live["milestone"] != issue["milestone"]:
            raise RoadmapError(f"live milestone drift for {issue['id']}")
    graph = graph_from_seed(live_seed, generated_at=seed.get("reviewedAt"), source_kind="live")
    graph["sourceHash"] = source_hash({"live": live_by_id, "seedContract": seed["seedVersion"]})
    graph["newestIssueUpdatedAt"] = max((entry["updatedAt"] for entry in graph["issues"]), default=graph["generatedAt"])
    return graph


def publish(graph: dict[str, Any], *, snapshot_path: Path, index_path: Path, cache: bool = True) -> dict[str, Any]:
    snapshot = snapshot_from_graph(graph)
    index = index_from_graph(graph)
    write_json(snapshot_path, snapshot)
    write_json(index_path, index)
    if cache:
        write_json(CACHE_PATH / "roadmap.v1.json", graph)
        write_json(CACHE_PATH / "fetched-at.json", {"generatedAt": graph["generatedAt"], "sourceHash": graph["sourceHash"]})
    return {"sourceHash": graph["sourceHash"], "generatedAt": graph["generatedAt"], "snapshot": str(snapshot_path), "index": str(index_path)}


def fallback(seed: dict[str, Any], *, snapshot_path: Path, index_path: Path) -> dict[str, Any]:
    cache_path = CACHE_PATH / "roadmap.v1.json"
    if not cache_path.exists() or not snapshot_path.exists():
        raise RoadmapError("no complete last-known-good graph is available")
    graph = load_json(cache_path)
    previous = load_json(snapshot_path)
    select_fallback_snapshot(previous)
    graph["sourceKind"] = "fallback"
    graph["fallbackUsed"] = True
    graph["fallbackReason"] = "live fetch failed"
    return publish(graph, snapshot_path=snapshot_path, index_path=index_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    parser.add_argument("--graph", type=Path, help="offline complete normalized graph fixture")
    parser.add_argument("--live", action="store_true", help="read bounded GitHub issue metadata")
    parser.add_argument("--allow-fallback", action="store_true", help="use a fresh complete cached graph on live failure")
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--index", type=Path, default=INDEX_PATH)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    seed = load_seed(args.seed)
    try:
        if args.live:
            graph = fetch_live(seed)
        elif args.graph:
            graph = load_json(args.graph)
            graph["sourceKind"] = "fixture"
        else:
            graph = graph_from_seed(seed, generated_at=seed.get("reviewedAt"), source_kind="seed")
        result = publish(graph, snapshot_path=args.snapshot, index_path=args.index, cache=not args.no_cache)
    except RoadmapError:
        if not args.live or not args.allow_fallback:
            raise
        result = fallback(seed, snapshot_path=args.snapshot, index_path=args.index)
        result["fallbackUsed"] = True
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
