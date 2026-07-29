#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "agents" / "task-dag.json").read_text())


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, check=check, capture_output=True)


def branch_for(task_id: str) -> str | None:
    result = run(
        "git",
        "for-each-ref",
        "--format=%(refname:short)",
        f"refs/heads/agent/{task_id}-*",
    )
    branches = [line for line in result.stdout.splitlines() if line]
    if len(branches) > 1:
        raise SystemExit(f"multiple branches found for {task_id}: {branches}")
    return branches[0] if branches else None


def prerequisite_is_merged(task_id: str, integration: str) -> bool:
    branch = branch_for(task_id)
    if branch is None:
        return False
    return run(
        "git", "merge-base", "--is-ancestor", branch, integration, check=False
    ).returncode == 0


def main() -> int:
    wave = int(sys.argv[1] if len(sys.argv) > 1 else "1")
    integration = DATA["integrationBranch"]
    if run("git", "show-ref", "--verify", "--quiet", f"refs/heads/{integration}", check=False).returncode:
        run("git", "branch", integration, "HEAD")

    selected = [task for task in DATA["tasks"] if task["parallelGroup"] == wave]
    if not selected:
        raise SystemExit(f"unknown or empty wave {wave}")

    if any(task.get("mvpPlus") for task in selected):
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "ci" / "check-mvp-plus-gate.py")],
            cwd=ROOT,
            check=True,
        )

    missing: list[str] = []
    for task in selected:
        for dependency in task["dependsOn"]:
            if dependency == "BASE_MVP_PASS":
                continue
            if not prerequisite_is_merged(dependency, integration):
                missing.append(f"{task['id']} requires merged {dependency}")
    if missing:
        raise SystemExit("wave prerequisites are not integrated:\n  " + "\n  ".join(missing))

    for task in selected:
        subprocess.run(
            [str(ROOT / "tools" / "agents" / "create-worktree.sh"), task["id"], task["slug"]],
            cwd=ROOT,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
