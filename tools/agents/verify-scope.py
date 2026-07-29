#!/usr/bin/env python3
"""Verify changed files are covered by a task packet's allowed glob patterns."""
from __future__ import annotations
import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def git_lines(*args: str) -> list[str]:
    proc = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    if proc.returncode:
        raise SystemExit(proc.stderr.strip() or 'git failed')
    return [line for line in proc.stdout.splitlines() if line]

def matches(path: str, pattern: str) -> bool:
    if pattern.endswith('/**'):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + '/')
    return fnmatch.fnmatchcase(path, pattern)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('task')
    parser.add_argument('--base')
    args = parser.parse_args()
    task = args.task.upper()
    allow_file = ROOT / 'agents' / 'tasks' / task / 'allowed-paths.txt'
    if not allow_file.exists():
        raise SystemExit(f'unknown task {task}')
    patterns = [line.strip() for line in allow_file.read_text().splitlines() if line.strip() and not line.startswith('#')]
    base = args.base
    if base is None:
        for candidate in ('integration/mvp-night', 'main', 'HEAD~1'):
            if subprocess.run(['git', 'rev-parse', '--verify', candidate], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                base = candidate
                break
    if base is None:
        raise SystemExit('could not determine comparison base')
    changed = set(git_lines('diff', '--name-only', f'{base}...HEAD'))
    changed.update(git_lines('diff', '--name-only'))
    changed.update(git_lines('diff', '--name-only', '--cached'))
    bad = sorted(path for path in changed if not any(matches(path, pattern) for pattern in patterns))
    if bad:
        print(f'{task}: out-of-scope files:', file=sys.stderr)
        for path in bad:
            print(f'  {path}', file=sys.stderr)
        return 1
    print(f'{task}: scope OK ({len(changed)} changed files, {len(patterns)} patterns)')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
