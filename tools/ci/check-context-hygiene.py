#!/usr/bin/env python3
"""Keep agent instructions and canonical docs intentionally small."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


for path in ROOT.rglob("AGENTS.md"):
    if "podroid" in path.parts or any(part in {".git", ".worktrees"} for part in path.parts):
        continue
    limit = 120 if path == ROOT / "AGENTS.md" else 80
    assert lines(path) <= limit, f"{path.relative_to(ROOT)} exceeds {limit} lines"

for path in (ROOT / "agents/tasks").glob("T*/task.md"):
    assert lines(path) <= 120, f"{path.relative_to(ROOT)} task packet is too large"
for path in (ROOT / "agents/tasks").glob("T*/context.list"):
    count = sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    assert count <= 12, f"{path.relative_to(ROOT)} requests {count} context files"

for path in (ROOT / "docs").rglob("*.md"):
    assert lines(path) <= 300, f"{path.relative_to(ROOT)} exceeds 300 lines; split it"

print("agent context-hygiene limits OK")
