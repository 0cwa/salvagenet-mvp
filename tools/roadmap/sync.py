#!/usr/bin/env python3
"""Generate or check complete roadmap snapshots with reviewed metadata.

The live issue graph owns planning state and dependencies. Acceptance IDs and
bounded context paths remain reviewed repository metadata; issue closure never
changes gate status. Only transient transport failures may use a recent complete
snapshot; structural graph errors always fail.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys

import roadmap
from catalog import configure_live, configure_roadmap

configure_roadmap(roadmap)

import live  # noqa: E402

configure_live(live, roadmap)

from live import PR_REFERENCE_RE, RoadmapTransportError, StrictGitHubClient, fetch_validated_live_graph  # noqa: E402


def enrich(graph: dict, seed: dict) -> dict:
    reviewed = {item["id"]: item for item in seed["items"]}
    for item_id, item in graph["items"].items():
        source = reviewed[item_id]
        item["acceptanceIds"] = list(source["acceptanceIds"])
        item["contextPaths"] = list(source["contextPaths"])
        if not item.get("summary"):
            item["summary"] = source["summary"]
        if not item.get("taskPacket"):
            item["taskPacket"] = source.get("taskPacket")
        if "pullRequestNumbers" not in item:
            source_text = json.dumps(source, sort_keys=True)
            item["pullRequestNumbers"] = sorted(
                {int(match.group("number")) for match in PR_REFERENCE_RE.finditer(source_text)}
            )
        if "pullRequests" not in item:
            item["pullRequests"] = [
                {
                    "number": number,
                    "state": "unknown",
                    "draft": None,
                    "merged": None,
                    "mergedAt": None,
                    "url": None,
                    "headSha": None,
                }
                for number in item["pullRequestNumbers"]
            ]
    return graph


def project_pull_requests(snapshot: dict, index: dict, graph: dict) -> None:
    graph_items = graph["items"]
    disagreements = list(snapshot.get("disagreements", []))
    snapshot_by_id = {item["id"]: item for item in snapshot["items"]}

    for item_id, item in snapshot_by_id.items():
        pulls = copy.deepcopy(graph_items[item_id].get("pullRequests", []))
        item["pullRequests"] = pulls
        if item["workState"] in {"active", "review"} and pulls:
            if all(pull.get("merged") or pull.get("state") == "closed" for pull in pulls):
                disagreements.append(
                    f"{item_id} is {item['workState']} but all linked pull requests are closed or merged"
                )
        if item["workState"] == "done" and any(
            pull.get("state") == "open" and not pull.get("merged") for pull in pulls
        ):
            disagreements.append(f"{item_id} is done while a linked pull request remains open")

    normalized = {
        "repository": snapshot["source"]["repository"],
        "milestones": snapshot["milestones"],
        "items": snapshot["items"],
    }
    source_hash = roadmap.sha256_json(normalized)
    snapshot["source"]["sourceHash"] = source_hash
    snapshot["disagreements"] = sorted(set(disagreements))

    source_by_id = {item["id"]: item for item in snapshot["items"]}
    for key in ("active", "ready", "blocked"):
        for item in index.get(key, []):
            source = source_by_id[item["id"]]
            item["pullRequests"] = copy.deepcopy(source["pullRequests"])
    index["sourceHash"] = source_hash
    index["disagreements"] = list(snapshot["disagreements"])


def recent_committed_fallback(reason: str, max_age_hours: int) -> tuple[dict, dict]:
    if not roadmap.SNAPSHOT_PATH.is_file() or not roadmap.INDEX_PATH.is_file():
        raise roadmap.RoadmapError(f"no committed last-known-good snapshot is available; live failure: {reason}")
    snapshot = roadmap.read_json(roadmap.SNAPSHOT_PATH)
    index = roadmap.read_json(roadmap.INDEX_PATH)
    generated = snapshot.get("generatedAt")
    if not isinstance(generated, str):
        raise roadmap.RoadmapError("fallback snapshot has no generatedAt")
    age = dt.datetime.now(dt.timezone.utc) - roadmap.parse_time(generated)
    if age > dt.timedelta(hours=max_age_hours):
        raise roadmap.RoadmapError(f"fallback snapshot is older than {max_age_hours} hours ({age}); live failure: {reason}")
    snapshot = copy.deepcopy(snapshot)
    snapshot.setdefault("source", {})["fallback"] = True
    snapshot["source"]["fallbackReason"] = reason[:500]
    snapshot["source"]["snapshotAgeSeconds"] = int(age.total_seconds())
    return snapshot, index


def live_projection(seed: dict, token: str) -> tuple[dict, dict]:
    graph = fetch_validated_live_graph(StrictGitHubClient(seed["repository"], token))
    graph = enrich(graph, seed)
    snapshot, index = roadmap.derive_snapshot(graph, fallback=False)
    project_pull_requests(snapshot, index, graph)
    return snapshot, index


def seed_projection(seed: dict) -> tuple[dict, dict]:
    graph = enrich(roadmap.seed_graph(seed), seed)
    snapshot, index = roadmap.derive_snapshot(graph, fallback=True)
    project_pull_requests(snapshot, index, graph)
    snapshot["source"]["fallbackReason"] = "reviewed pre-bootstrap catalog projection"
    return snapshot, index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--strict-live", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--max-age-hours", type=int, default=72)
    args = parser.parse_args()

    if args.seed_only and args.check:
        raise roadmap.RoadmapError("--check requires the live graph; it cannot be combined with --seed-only")

    seed = roadmap.load_seed()
    roadmap.validate_seed(seed)
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")

    if args.seed_only:
        snapshot, index = seed_projection(seed)
    elif token:
        try:
            snapshot, index = live_projection(seed, token)
        except RoadmapTransportError as exc:
            if args.strict_live or args.check:
                raise roadmap.RoadmapError(str(exc)) from exc
            snapshot, index = recent_committed_fallback(str(exc), args.max_age_hours)
    elif args.strict_live or args.check:
        raise roadmap.RoadmapError("GH_TOKEN or GITHUB_TOKEN is required for strict live generation")
    elif roadmap.SNAPSHOT_PATH.is_file() and roadmap.INDEX_PATH.is_file():
        snapshot, index = recent_committed_fallback(
            "live fetch not requested because no token is available", args.max_age_hours
        )
    else:
        snapshot, index = seed_projection(seed)

    if args.check:
        committed = roadmap.read_json(roadmap.SNAPSHOT_PATH)
        committed_hash = committed.get("source", {}).get("sourceHash")
        live_hash = snapshot.get("source", {}).get("sourceHash")
        if committed_hash != live_hash:
            raise roadmap.RoadmapError(f"roadmap snapshot is stale: committed={committed_hash} live={live_hash}")
        generated = committed.get("generatedAt")
        if not isinstance(generated, str):
            raise roadmap.RoadmapError("committed roadmap snapshot has no generatedAt")
        age = dt.datetime.now(dt.timezone.utc) - roadmap.parse_time(generated)
        if age > dt.timedelta(hours=args.max_age_hours):
            raise roadmap.RoadmapError(f"committed roadmap snapshot is older than {args.max_age_hours} hours")
        print("roadmap snapshot is current")
        return 0

    if args.write:
        roadmap.write_snapshots(snapshot, index)
    print(
        json.dumps(
            {
                "snapshot": str(roadmap.SNAPSHOT_PATH.relative_to(Path.cwd()))
                if roadmap.SNAPSHOT_PATH.is_relative_to(Path.cwd())
                else str(roadmap.SNAPSHOT_PATH),
                "index": str(roadmap.INDEX_PATH.relative_to(Path.cwd()))
                if roadmap.INDEX_PATH.is_relative_to(Path.cwd())
                else str(roadmap.INDEX_PATH),
                "sourceHash": snapshot["source"]["sourceHash"],
                "fallback": snapshot["source"].get("fallback", False),
                "fallbackReason": snapshot["source"].get("fallbackReason"),
                "items": len(snapshot["items"]),
                "disagreements": snapshot["disagreements"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except roadmap.RoadmapError as exc:
        print(f"roadmap error: {exc}", file=sys.stderr)
        raise SystemExit(2)
