#!/usr/bin/env bash
set -euo pipefail
[[ $# -ge 1 && $# -le 2 ]] || { echo "usage: $0 Txx [slug]" >&2; exit 2; }
task=${1^^}
root=$(git rev-parse --show-toplevel)
cd "$root"
[[ -f "agents/tasks/$task/task.md" ]] || { echo "unknown task $task" >&2; exit 2; }
slug=${2:-$(python3 - "$task" <<'PY'
import json, sys
from pathlib import Path
root=Path.cwd()
task=sys.argv[1]
data=json.loads((root/'agents/task-dag.json').read_text())
print(next(item['slug'] for item in data['tasks'] if item['id']==task))
PY
)}
integration=$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('agents/task-dag.json').read_text())['integrationBranch'])
PY
)
if ! git show-ref --verify --quiet "refs/heads/$integration"; then
  git branch "$integration" HEAD
  echo "created integration branch $integration at HEAD" >&2
fi
branch="agent/$task-$slug"
dir="$root/.worktrees/$task-$slug"
mkdir -p "$root/.worktrees"
if git show-ref --verify --quiet "refs/heads/$branch"; then
  if git worktree list --porcelain | grep -Fxq "worktree $dir"; then
    printf '%s\n' "$dir"
    exit 0
  fi
  git worktree add "$dir" "$branch"
else
  git worktree add -b "$branch" "$dir" "$integration"
fi
printf '%s\n' "$dir"
