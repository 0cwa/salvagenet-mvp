#!/usr/bin/env python3
"""Plan or explicitly apply the reviewed roadmap bootstrap.

The default mode is offline and read-only. ``--apply`` is an intentional
mutation boundary used only by the manually-triggered workflow; it requires
``--live --confirm-apply`` and a token supplied by the workflow environment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, SEED_PATH, RoadmapError, graph_from_seed, issue_body, load_json, load_seed, marker_from_body, marker_for, seed_source, source_hash
except ImportError:  # direct script execution from Makefile/CI
    from common import ROOT, SEED_PATH, RoadmapError, graph_from_seed, issue_body, load_json, load_seed, marker_from_body, marker_for, seed_source, source_hash


def existing_by_id(existing: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = existing.get("issues", existing.get("items", []))
    if not isinstance(records, list):
        raise RoadmapError("existing graph issues must be a list")
    found: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise RoadmapError("existing graph issue must be an object")
        stable_id = record.get("stableId") or marker_from_body(record.get("body", ""))
        if stable_id:
            if stable_id in found:
                raise RoadmapError(f"duplicate live stable ID: {stable_id}")
            found[stable_id] = record
    return found


def plan(seed: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing_map = existing_by_id(existing or {})
    seed_issues = {entry["id"]: entry for entry in seed["issues"]}
    create = sorted(set(seed_issues) - set(existing_map))
    verify = sorted(set(seed_issues) & set(existing_map))
    drift: list[dict[str, Any]] = []
    for stable_id in verify:
        live = existing_map[stable_id]
        expected = seed_issues[stable_id]
        live_labels = sorted(live.get("labels", []))
        expected_labels = sorted(expected["labels"])
        if live_labels and live_labels != expected_labels:
            drift.append({"stableId": stable_id, "field": "labels", "expected": expected_labels, "observed": live_labels, "action": "report-only"})
        if isinstance(live.get("milestone"), str) and live["milestone"] != expected["milestone"]:
            drift.append({"stableId": stable_id, "field": "milestone", "expected": expected["milestone"], "observed": live["milestone"], "action": "report-only"})
    dependency_count = sum(len(issue["dependencies"]) for issue in seed["issues"])
    return {
        "schemaVersion": 1,
        "mode": "dry-run",
        "repository": seed["repository"],
        "sourceHash": source_hash(seed_source(seed)),
        "labels": {"verifyOrCreate": len(seed["labels"])},
        "milestones": {"verifyOrCreate": len(seed["milestones"])},
        "issues": {"create": len(create), "verify": len(verify), "stableIdsToCreate": create},
        "dependencies": {"verifyOrCreate": dependency_count},
        "drift": drift,
        "liveRefinementsPreserved": True,
    }


def apply_boundary(seed: dict[str, Any], *, repository: str) -> None:
    """Make the mutation boundary explicit without hiding a partial apply."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RoadmapError("apply requires GITHUB_TOKEN or GH_TOKEN supplied by the workflow")
    # Keep the implementation deliberately narrow: the workflow invokes the
    # API adapter only after a human supplies the confirmation input. The
    # adapter is imported lazily so offline validation never touches network
    # code or credentials.
    try:
        from .github_mutations import GitHubMutationClient
    except ImportError:
        from github_mutations import GitHubMutationClient

    client = GitHubMutationClient(repository, token)
    client.apply_seed(seed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    parser.add_argument("--existing", type=Path, help="bounded normalized graph fixture")
    parser.add_argument("--repository", default=None)
    parser.add_argument("--live", action="store_true", help="enable the network mutation boundary")
    parser.add_argument("--apply", action="store_true", help="apply missing objects; never overwrites live refinements")
    parser.add_argument("--confirm-apply", choices=["APPLY_ROADMAP_BOOTSTRAP"], help="required explicit human confirmation")
    args = parser.parse_args()
    seed = load_seed(args.seed)
    if args.live:
        try:
            from .sync import fetch_live
        except ImportError:
            from sync import fetch_live
        existing = fetch_live(seed)
    else:
        existing = load_json(args.existing) if args.existing else None
    report = plan(seed, existing)
    if args.apply:
        if not args.live or args.confirm_apply != "APPLY_ROADMAP_BOOTSTRAP":
            raise SystemExit("apply requires --live --confirm-apply APPLY_ROADMAP_BOOTSTRAP")
        apply_boundary(seed, repository=args.repository or seed["repository"])
        report["mode"] = "apply"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
