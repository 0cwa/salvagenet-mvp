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
registered_branch=$(git worktree list --porcelain | awk -v target="$dir" '
  $1=="worktree" { path=$2; branch="" }
  $1=="branch" { branch=$2 }
  path==target && branch!="" { print branch; exit }
')
if [[ -n "$registered_branch" ]]; then
  if [[ "$registered_branch" != "refs/heads/$integration" ]]; then
    echo "$dir is attached to $registered_branch, but the active cycle requires refs/heads/$integration" >&2
    echo "remove or relocate the stale integration worktree before continuing" >&2
    exit 2
  fi
  printf '%s\n' "$dir"
  exit 0
fi
if [[ -e "$dir" ]]; then
  echo "$dir exists but is not a registered Git worktree; move or remove it first" >&2
  exit 2
fi
git worktree add "$dir" "$integration"
printf '%s\n' "$dir"
