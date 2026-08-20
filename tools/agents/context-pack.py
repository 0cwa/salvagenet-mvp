#!/usr/bin/env python3
"""Build a deterministic, scoped Markdown context pack for one task."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUDGET = 120_000
EXCLUDED_PARTS = {'.git', '.local', 'build', '.gradle', 'secrets'}
CORE_CONTEXT = (
    'docs/product/north-star.md',
    'GOAL.md',
    'AGENTS.md',
)


def applicable_agents(path: Path) -> list[Path]:
    out: list[Path] = []
    cur = path.parent
    while True:
        candidate = cur / 'AGENTS.md'
        if candidate.exists() and (
            candidate.resolve() == ROOT / 'AGENTS.md'
            or ROOT in candidate.resolve().parents
        ):
            out.append(candidate)
        if cur == ROOT:
            break
        if ROOT not in cur.resolve().parents:
            break
        cur = cur.parent
    return list(reversed(out))


def checked_path(raw: str) -> Path | None:
    path = (ROOT / raw).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise SystemExit(f'context escapes repository: {raw}')
    if any(part in EXCLUDED_PARTS for part in path.parts):
        raise SystemExit(f'forbidden context path: {raw}')
    return path if path.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('task')
    parser.add_argument('--budget', type=int, default=DEFAULT_BUDGET)
    parser.add_argument('--stdout', action='store_true')
    args = parser.parse_args()
    task = args.task.upper()
    context_list = ROOT / 'agents' / 'tasks' / task / 'context.list'
    if not context_list.exists():
        raise SystemExit(f'unknown task: {task}')

    requested: list[tuple[str, Path | None]] = []
    for raw in context_list.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        requested.append((raw, checked_path(raw)))

    # Every implementation task receives the durable product direction, the
    # bounded current milestone, and repository rules. The full strategic
    # roadmap is intentionally not injected; phase planning uses its bounded
    # issue context and strategic-priorities document separately.
    ordered: list[tuple[str, Path | None]] = [
        (raw, checked_path(raw)) for raw in CORE_CONTEXT
    ]
    seen: set[str] = set(CORE_CONTEXT)

    for raw, path in requested:
        if path:
            for agent_file in applicable_agents(path):
                rel = agent_file.relative_to(ROOT).as_posix()
                if rel not in seen:
                    ordered.append((rel, agent_file))
                    seen.add(rel)
        if raw not in seen:
            ordered.append((raw, path))
            seen.add(raw)

    chunks = [f'# Context pack: {task}\n']
    total = len(chunks[0].encode())
    for rel, path in ordered:
        body = (
            '[MISSING BEFORE PREREQUISITE/IMPORT]\n'
            if path is None
            else path.read_text(errors='replace')
        )
        chunk = f'\n## FILE: {rel}\n\n```text\n{body.rstrip()}\n```\n'
        size = len(chunk.encode())
        if total + size > args.budget:
            raise SystemExit(
                f'context budget exceeded at {rel}: {total + size}>{args.budget}'
            )
        chunks.append(chunk)
        total += size

    output = ''.join(chunks)
    target = ROOT / '.local' / 'context' / f'{task}.md'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output)
    print(
        output
        if args.stdout
        else f'{target.relative_to(ROOT)} ({total} bytes, {len(ordered)} files)'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
