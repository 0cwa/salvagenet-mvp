#!/usr/bin/env python3
"""Safely create a compact task packet without pre-authorizing future work."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ID = re.compile(r"^[A-Z][0-9]{2}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SPECIAL_DEPENDENCIES = {"BASE_MVP_PASS"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def build(args):
    task = args.id.upper()
    activate = bool(getattr(args, "activate", False))
    if not ID.fullmatch(task):
        raise ValueError("--id must look like F02")
    if not SLUG.fullmatch(args.slug):
        raise ValueError("--slug must be lower-kebab-case")
    if not args.allowed_path:
        raise ValueError("at least one --allowed-path is required")
    if not args.acceptance:
        raise ValueError("at least one --acceptance is required")
    for value in [*args.allowed_path, *args.context]:
        if value.startswith("/") or ".." in Path(value).parts:
            raise ValueError(f"path must stay repository-relative: {value}")
    missing = [value for value in args.context if not (ROOT / value).is_file()]
    if missing:
        raise ValueError(f"missing context files: {missing}")
    if len(args.context) > 12:
        raise ValueError("context list may contain at most 12 paths")

    dag = load(ROOT / "agents/task-dag.json")
    registry = load(ROOT / "agents/task-registry.json")
    active_ids = {item["id"] for item in dag["tasks"]}
    registry_by_id = {item["id"]: item for item in registry["tasks"]}
    if task in registry_by_id or (ROOT / "agents/tasks" / task).exists():
        raise ValueError(f"task already exists: {task}")

    unknown = set(args.depends_on) - set(registry_by_id) - SPECIAL_DEPENDENCIES
    if unknown:
        raise ValueError(f"unknown dependencies: {sorted(unknown)}")

    if activate:
        blocked = [
            dependency
            for dependency in args.depends_on
            if dependency not in SPECIAL_DEPENDENCIES
            and dependency not in active_ids
            and registry_by_id[dependency].get("status") != "MERGED"
        ]
        if blocked:
            raise ValueError(
                "active task dependencies must be active or merged: " + ", ".join(sorted(blocked))
            )
        dag["tasks"].append(
            {
                "id": task,
                "slug": args.slug,
                "dependsOn": args.depends_on,
                "parallelGroup": args.group,
                "mvpPlus": args.mvp_plus,
            }
        )

    status = "PLANNED" if activate else "QUEUED_REVIEW"
    registry["tasks"].append(
        {
            "id": task,
            "name": args.name,
            "dependsOn": args.depends_on,
            "packet": f"agents/tasks/{task}/task.md",
            "status": status,
        }
    )
    registry.setdefault("cycleStatus", {})[task] = status

    acceptance = "\n".join(f"- {item}" for item in args.acceptance)
    prerequisites = ", ".join(args.depends_on) if args.depends_on else "None."
    task_md = f"""# {task} — {args.name}

## Status

**{status.replace('_', ' ')}.**

## Outcome

{args.outcome}

## Prerequisites

{prerequisites}

## Phase-start review

Re-evaluate this packet against current `main` before activation. Confirm prerequisites, allowed paths, acceptance criteria, evidence limits, and whether the task should be split, narrowed, reordered, or removed.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff and phase-plan review.

## Acceptance criteria

{acceptance}

## Required checks

```sh
make validate
python3 tools/agents/verify-scope.py {task}
```

## Phase-end verification

Check every acceptance criterion against code, tests, package artifacts, and evidence. Run the full applicable CI workflow before merge-ready status, then re-evaluate the next phase from the actual result.

## Handoff

Report commit SHA(s), tests, unavailable checks, evidence paths, concrete deferred items, every acceptance result, and the smallest next blocker.
"""
    return task, dag, registry, task_md


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--outcome", default="Implement the scoped task outcome.")
    parser.add_argument("--group", type=int, required=True)
    parser.add_argument("--depends-on", action="append", default=[])
    parser.add_argument("--allowed-path", action="append", default=[])
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--acceptance", action="append", default=[])
    parser.add_argument("--mvp-plus", action="store_true")
    parser.add_argument(
        "--activate",
        action="store_true",
        help="also add the task to the active DAG; default is queued for phase review",
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        task, dag, registry, task_md = build(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None

    dag_entry = dag["tasks"][-1] if args.activate else None
    preview = {
        "task": task,
        "status": registry["cycleStatus"][task],
        "dagEntry": dag_entry,
        "allowedPaths": args.allowed_path,
        "context": args.context,
        "acceptance": args.acceptance,
    }
    if not args.write:
        print(json.dumps(preview, indent=2))
        print("dry-run: pass --write to create a queued packet; add --activate only after phase review")
        return 0

    target = ROOT / "agents/tasks" / task
    target.mkdir(parents=True)
    files = {
        target / "task.md": task_md,
        target / "allowed-paths.txt": "\n".join(args.allowed_path) + "\n",
        target / "context.list": "\n".join(args.context) + "\n",
        target / "README.md": (
            f"# {task}\n\nStatus: **{registry['cycleStatus'][task]}**. "
            f"Generate context with `make context TASK={task}` after phase review.\n"
        ),
    }
    for path, body in files.items():
        path.write_text(body, encoding="utf-8")
    for path, data in (
        (ROOT / "agents/task-dag.json", dag),
        (ROOT / "agents/task-registry.json", registry),
    ):
        temporary = path.with_suffix(path.suffix + ".tmp")
        dump(temporary, data)
        temporary.replace(path)
    print(json.dumps(preview, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
