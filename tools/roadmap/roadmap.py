#!/usr/bin/env python3
"""Stable repository entry point for roadmap status, freshness, sync, and context."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import INDEX_PATH, SNAPSHOT_PATH, RoadmapError, load_json, snapshot_freshness, validate_graph
except ImportError:  # direct script execution from Makefile/CI
    from common import INDEX_PATH, SNAPSHOT_PATH, RoadmapError, load_json, snapshot_freshness, validate_graph


def run_script(name: str, argv: list[str]) -> int:
    return subprocess.run([sys.executable, str(Path(__file__).with_name(name)), *argv]).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-seed")
    sub.add_parser("sync")
    sub.add_parser("bootstrap")
    status = sub.add_parser("status")
    status.add_argument("--index", type=Path, default=INDEX_PATH)
    freshness = sub.add_parser("freshness")
    freshness.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    context = sub.add_parser("context")
    context.add_argument("issue")
    context.add_argument("--debug-comments", action="store_true")
    context.add_argument("--comments", type=Path)
    args, passthrough = parser.parse_known_args()
    if args.command == "validate-seed":
        return run_script("validate_seed.py", passthrough)
    if args.command == "sync":
        return run_script("sync.py", passthrough)
    if args.command == "bootstrap":
        return run_script("bootstrap.py", passthrough)
    if args.command == "status":
        index = load_json(args.index)
        print(json.dumps({"schemaVersion": index.get("schemaVersion"), "generatedAt": index.get("generatedAt"), "source": index.get("source"), "currentMilestone": index.get("currentMilestone"), "counts": {key: len(index.get(key, [])) for key in ("active", "ready", "blocked")}, "disagreements": index.get("disagreements", [])}, indent=2, sort_keys=True))
        return 0
    if args.command == "freshness":
        snapshot = load_json(args.snapshot)
        result = snapshot_freshness(snapshot, now=datetime.now(timezone.utc))
        print(json.dumps({**result, "generatedAt": snapshot.get("generatedAt"), "source": snapshot.get("source")}, indent=2, sort_keys=True))
        return 0 if result["fresh"] else 1
    if args.command == "context":
        argv = [args.issue]
        if args.debug_comments:
            argv.append("--debug-comments")
        if args.comments:
            argv.extend(["--comments", str(args.comments)])
        return run_script("context.py", argv)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
