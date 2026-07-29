#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[2]
data = json.loads((root / 'agents/task-dag.json').read_text())
print('TASK  BRANCH/HEAD                              WORKTREE')
worktrees = subprocess.run(['git', 'worktree', 'list', '--porcelain'], cwd=root, text=True, capture_output=True).stdout
for task in data['tasks']:
    prefix = f"agent/{task['id']}-"
    refs = subprocess.run(['git', 'for-each-ref', '--format=%(refname:short) %(objectname:short)', f'refs/heads/{prefix}*'], cwd=root, text=True, capture_output=True).stdout.strip()
    print(f"{task['id']:<5} {refs or '-':<40} {'yes' if task['id'] in worktrees else 'no'}")
