#!/usr/bin/env python3
"""Stable CLI for reviewed roadmap seed validation and bootstrap."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from roadmap import GitHubClient, RoadmapError, bootstrap, load_seed, validate_seed


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-seed")
    apply_parser = sub.add_parser("bootstrap")
    apply_parser.add_argument("--apply", action="store_true")
    apply_parser.add_argument("--state-output", type=Path)
    args = parser.parse_args()

    seed = load_seed()
    if args.command == "validate-seed":
        print(json.dumps(validate_seed(seed), indent=2, sort_keys=True))
        return 0
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise RoadmapError("GH_TOKEN or GITHUB_TOKEN is required for live bootstrap")
    result = bootstrap(seed, GitHubClient(seed["repository"], token), args.apply, args.state_output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RoadmapError as exc:
        print(f"roadmap error: {exc}", file=sys.stderr)
        raise SystemExit(2)
