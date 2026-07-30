#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[2]
dag = json.loads((root / "agents/task-dag.json").read_text(encoding="utf-8"))
registry = json.loads((root / "agents/task-registry.json").read_text(encoding="utf-8"))
registry_by_id = {item["id"]: item for item in registry["tasks"]}
active_ids = {item["id"] for item in dag["tasks"]}

phase = dag.get("phase", {})
print("PHASE", phase.get("id", "unknown"))
print(phase.get("objective", ""))
print("TASK  STATUS        BRANCH/HEAD                              WORKTREE")
worktrees = subprocess.run(
    ["git", "worktree", "list", "--porcelain"],
    cwd=root,
    text=True,
    capture_output=True,
).stdout
for task in dag["tasks"]:
    task_id = task["id"]
    prefix = "agent/" + task_id + "-"
    refs = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short) %(objectname:short)", "refs/heads/" + prefix + "*"],
        cwd=root,
        text=True,
        capture_output=True,
    ).stdout.strip()
    status = registry_by_id[task_id].get("status", "UNKNOWN")
    print(f"{task_id:<5} {status:<13} {refs or '-':<40} {'yes' if task_id in worktrees else 'no'}")

print("\nQUEUED / COMPLETED")
for item in registry["tasks"]:
    if item["id"] in active_ids:
        continue
    suffix = ""
    if item.get("mergeCommit"):
        suffix = " merge=" + item["mergeCommit"][:12]
    print(f"{item['id']:<5} {item.get('status', 'UNKNOWN'):<14} {item['name']}{suffix}")
