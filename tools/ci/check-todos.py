#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
this_file = Path(__file__).resolve()
ignore = {'.git', '.local', '.gradle', '.worktrees', 'build', '.venv', 'podroid'}
allowed = re.compile(r'TODO\((MVP-HARDENING|RESEARCH), T\d\d\):')

for path in root.rglob('*'):
    if not path.is_file() or path.resolve() == this_file:
        continue
    if any(part in ignore for part in path.relative_to(root).parts):
        continue
    if path.suffix not in {'.kt', '.java', '.py', '.sh', '.c', '.h'}:
        continue
    for line_number, line in enumerate(path.read_text(errors='ignore').splitlines(), 1):
        if 'TODO' in line and not allowed.search(line):
            raise SystemExit(
                f'{path.relative_to(root)}:{line_number}: '
                f'TODO must be scoped: {line.strip()}'
            )

print('scoped TODO policy OK')
