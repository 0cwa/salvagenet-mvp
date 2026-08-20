#!/usr/bin/env python3
"""Keep agent instructions and canonical docs intentionally small."""
from __future__ import annotations
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def lines(path:Path)->int: return len(path.read_text(encoding='utf-8',errors='replace').splitlines())
for path in ROOT.rglob('AGENTS.md'):
    if 'podroid' in path.parts or any(part in {'.git','.worktrees'} for part in path.parts):
        continue
    limit=120 if path==ROOT/'AGENTS.md' else 80
    assert lines(path)<=limit,f'{path.relative_to(ROOT)} exceeds {limit} lines'
for packet in sorted((ROOT/'agents/tasks').iterdir()):
    if not packet.is_dir() or not (packet/'task.md').is_file():
        continue
    assert lines(packet/'task.md')<=120,f'{packet.relative_to(ROOT)}/task.md is too large'
    count=sum(1 for line in (packet/'context.list').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#'))
    assert count<=12,f'{packet.relative_to(ROOT)}/context.list requests {count} context files'
for path in (ROOT/'docs').rglob('*.md'):
    assert lines(path)<=300,f'{path.relative_to(ROOT)} exceeds 300 lines; split it'
print('agent context-hygiene limits OK')
