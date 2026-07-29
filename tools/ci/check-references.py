#!/usr/bin/env python3
"""Check repository-local Markdown links, task context paths, and template includes."""

from __future__ import annotations

import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
INCLUDE = re.compile(r"\{\{INCLUDE:([^}]+)\}\}")


def check_markdown_links(errors: list[str]) -> None:
    for path in ROOT.rglob("*.md"):
        if any(part in {".git", ".local", ".worktrees"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in MARKDOWN_LINK.findall(text):
            target = target.strip().split(" ", 1)[0].strip("<>")
            parsed = urlparse(target)
            if parsed.scheme or target.startswith(('#', 'mailto:')):
                continue
            relative = unquote(parsed.path)
            if not relative:
                continue
            resolved = (path.parent / relative).resolve()
            if resolved != ROOT and ROOT not in resolved.parents:
                errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {target}")
            elif not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing link target: {target}")


def check_task_context(errors: list[str]) -> None:
    dag = json.loads((ROOT / "agents/task-dag.json").read_text(encoding="utf-8"))
    by_id = {task["id"]: task for task in dag["tasks"]}
    for task_id in sorted(by_id):
        path = ROOT / "agents/tasks" / task_id / "context.list"
        for raw in path.read_text(encoding="utf-8").splitlines():
            relative = raw.strip()
            if not relative or relative.startswith("#"):
                continue
            target = (ROOT / relative).resolve()
            if target.is_file():
                continue
            # Podroid files are intentionally absent before T00 imports upstream.
            if relative.startswith("android/podroid/") and task_id != "T00":
                continue
            errors.append(f"{path.relative_to(ROOT)}: missing context file: {relative}")


def check_template_includes(errors: list[str]) -> None:
    for path in (ROOT / "profiles/guest-init").rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for relative in INCLUDE.findall(text):
            target = (ROOT / relative.strip()).resolve()
            if target != ROOT and ROOT not in target.parents:
                errors.append(f"{path.relative_to(ROOT)}: include escapes repository: {relative}")
            elif not target.is_file():
                errors.append(f"{path.relative_to(ROOT)}: missing include: {relative}")


def main() -> int:
    errors: list[str] = []
    check_markdown_links(errors)
    check_task_context(errors)
    check_template_includes(errors)
    if errors:
        raise SystemExit("\n".join(errors))
    print("repository references and guest-init includes OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
