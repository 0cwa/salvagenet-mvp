#!/usr/bin/env python3
"""Generate roadmap snapshots while keeping acceptance metadata seed-bound.

The live issue graph owns planning state and dependencies. Acceptance IDs and
bounded context paths remain reviewed repository metadata; issue closure never
changes gate status.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from commands import normalized_seed
from roadmap import (
    GitHubClient,
    INDEX_PATH,
    RoadmapError,
    SNAPSHOT_PATH,
    derive_snapshot,
    fetch_live_graph,
    seed_graph,
    validate_seed,
    write_snapshots,
)


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
    return graph


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--strict-live", action="store_true")
    args = parser.parse_args()

    seed = normalized_seed()
    validate_seed(seed)
    graph = seed_graph(seed)
    fallback = True
    if not args.seed_only:
        token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        if token:
            try:
                graph = fetch_live_graph(GitHubClient(seed["repository"], token))
                fallback = False
            except Exception:
                if args.strict_live:
                    raise
        elif args.strict_live:
            raise RoadmapError("GH_TOKEN or GITHUB_TOKEN is required for strict live generation")
    graph = enrich(graph, seed)
    snapshot, index = derive_snapshot(graph, fallback=fallback)
    if fallback:
        snapshot["source"]["fallbackReason"] = "reviewed bootstrap seed projection"
    if args.write:
        write_snapshots(snapshot, index)
    print(json.dumps({
        "snapshot": str(SNAPSHOT_PATH.relative_to(Path.cwd())) if SNAPSHOT_PATH.is_relative_to(Path.cwd()) else str(SNAPSHOT_PATH),
        "index": str(INDEX_PATH.relative_to(Path.cwd())) if INDEX_PATH.is_relative_to(Path.cwd()) else str(INDEX_PATH),
        "sourceHash": snapshot["source"]["sourceHash"],
        "fallback": fallback,
        "items": len(snapshot["items"]),
        "disagreements": snapshot["disagreements"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RoadmapError as exc:
        print(f"roadmap error: {exc}", file=sys.stderr)
        raise SystemExit(2)
