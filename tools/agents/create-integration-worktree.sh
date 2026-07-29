#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
integration=$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('agents/task-dag.json').read_text())['integrationBranch'])
PY
)
dir="$root/.worktrees/integration"
mkdir -p "$root/.worktrees"
if ! git show-ref --verify --quiet "refs/heads/$integration"; then
  git branch "$integration" HEAD
fi
if git worktree list --porcelain | grep -Fxq "worktree $dir"; then
  printf '%s\n' "$dir"
else
  git worktree add "$dir" "$integration"
  printf '%s\n' "$dir"
fi
