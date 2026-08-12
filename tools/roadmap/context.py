#!/usr/bin/env python3
"""Emit bounded context for one normalized roadmap issue."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .common import MAX_COMMENT_BYTES, MAX_COMMENT_COUNT, MAX_CONTEXT_BYTES, MAX_CONTEXT_FILES, ROOT, SEED_PATH, bounded_text, load_json, load_seed, marker_for
except ImportError:  # direct script execution from Makefile/CI
    from common import MAX_COMMENT_BYTES, MAX_COMMENT_COUNT, MAX_CONTEXT_BYTES, MAX_CONTEXT_FILES, ROOT, SEED_PATH, bounded_text, load_json, load_seed, marker_for


def find_issue(seed: dict[str, Any], selector: str) -> dict[str, Any]:
    for issue in seed["issues"]:
        if issue["id"] == selector or str(issue.get("issueNumber")) == selector:
            return issue
    raise SystemExit(f"roadmap issue not found: {selector}")


def load_comments(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    data = load_json(path)
    comments = data.get("comments", data if isinstance(data, list) else [])
    if not isinstance(comments, list):
        raise SystemExit("comments input must be a list or an object with comments")
    return sorted((entry for entry in comments if isinstance(entry, dict)), key=lambda entry: entry.get("createdAt", ""), reverse=True)[:MAX_COMMENT_COUNT]


def context_document(issue: dict[str, Any], *, debug_comments: bool = False, comments: list[dict[str, Any]] | None = None) -> str:
    paths = list(dict.fromkeys(issue["contextPaths"] + ([issue["taskPacket"]] if issue.get("taskPacket") else [])))
    if len(paths) > MAX_CONTEXT_FILES:
        raise SystemExit(f"context has {len(paths)} files; limit is {MAX_CONTEXT_FILES}")
    lines = [
        f"# Roadmap context: {issue['id']}", "", marker_for(issue["id"]), "",
        f"Issue number: {issue.get('issueNumber', 'unassigned')}",
        f"Title: {issue['title']}",
        f"Summary: {issue['publicSummary']}",
        f"Milestone: {issue['milestone']}",
        f"Work state: {issue['seedState']}",
        f"Dependencies: {', '.join(issue['dependencies']) or 'none'}",
        f"Acceptance IDs: {', '.join(issue['acceptanceIds']) or 'none'}",
        f"Task packet: {issue.get('taskPacket') or 'none'}", "",
        "State boundaries:",
        "- Issue state describes planned work only.",
        "- agents/task-dag.json and the active packet authorize implementation.",
        "- The acceptance ledger and reviewed evidence authorize product claims.",
        "- Pull-request state is reported separately.", "",
        "## Declared validation", "", *[f"- {entry}" for entry in issue["validation"]], "",
    ]
    total = len("\n".join(lines).encode("utf-8"))
    for raw_path in paths:
        path = (ROOT / raw_path).resolve()
        if path != ROOT and ROOT not in path.parents:
            raise SystemExit(f"context path escapes repository: {raw_path}")
        if not path.is_file():
            raise SystemExit(f"context path is missing: {raw_path}")
        text, truncated = bounded_text(path.read_text(errors="replace"), MAX_CONTEXT_BYTES - total)
        block = f"## FILE: {raw_path}\n\n```text\n{text.rstrip()}\n```\n"
        total += len(block.encode("utf-8"))
        lines.extend([block])
        if truncated:
            lines.append("[file truncated by context byte bound]\n")
            break
        if total >= MAX_CONTEXT_BYTES:
            break
    if debug_comments:
        lines.extend(["## DEBUG COMMENTS (bounded newest-first)", ""])
        used = 0
        bounded_comments = sorted((entry for entry in (comments or []) if isinstance(entry, dict)), key=lambda entry: entry.get("createdAt", ""), reverse=True)[:MAX_COMMENT_COUNT]
        for comment in bounded_comments:
            body, _ = bounded_text(str(comment.get("body", "")), MAX_COMMENT_BYTES - used)
            block = f"- {comment.get('createdAt', 'unknown')}: {body.strip()}\n"
            if used + len(block.encode("utf-8")) > MAX_COMMENT_BYTES:
                break
            lines.append(block)
            used += len(block.encode("utf-8"))
    output = "\n".join(lines)
    if len(output.encode("utf-8")) > MAX_CONTEXT_BYTES:
        output, _ = bounded_text(output, MAX_CONTEXT_BYTES)
    return output.rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue", help="stable roadmap ID or issue number")
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    parser.add_argument("--debug-comments", action="store_true", help="include only bounded newest-first comments")
    parser.add_argument("--comments", type=Path, help="offline bounded comments fixture; requires --debug-comments")
    args = parser.parse_args()
    if args.comments and not args.debug_comments:
        raise SystemExit("--comments requires --debug-comments")
    issue = find_issue(load_seed(args.seed), args.issue)
    print(context_document(issue, debug_comments=args.debug_comments, comments=load_comments(args.comments)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
