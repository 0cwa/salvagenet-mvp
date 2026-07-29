#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
this_file = Path(__file__).resolve()
ignore = {'.git', '.local', '.gradle', 'build', 'secrets', '.venv', 'podroid'}
patterns = [
    re.compile(r'tskey-(?:auth|client)-[A-Za-z0-9_-]{10,}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r"(?i)headscale.{0,20}api[_-]?key\s*[:=]\s*[\"']?[A-Za-z0-9_-]{20,}"),
]

for path in root.rglob('*'):
    if not path.is_file() or path.resolve() == this_file:
        continue
    if any(part in ignore for part in path.relative_to(root).parts):
        continue
    try:
        text = path.read_text(errors='ignore')
    except Exception:
        continue
    for pattern in patterns:
        if pattern.search(text):
            raise SystemExit(f'possible live secret in {path.relative_to(root)}')

print('secret-pattern scan OK')
