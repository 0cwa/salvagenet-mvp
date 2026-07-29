#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || { echo "usage: $0 Txx" >&2; exit 2; }
task=${1^^}
root=$(git rev-parse --show-toplevel)
cd "$root"
[[ -f "agents/tasks/$task/task.md" ]] || { echo "unknown task: $task" >&2; exit 2; }

integration=$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('agents/task-dag.json').read_text())['integrationBranch'])
PY
)
integration_dir="$root/.worktrees/integration"
if [[ ! -d "$integration_dir/.git" && ! -f "$integration_dir/.git" ]]; then
  tools/agents/create-integration-worktree.sh >/dev/null
fi

mapfile -t branches < <(git for-each-ref --format='%(refname:short)' "refs/heads/agent/$task-*" )
[[ ${#branches[@]} -eq 1 ]] || {
  echo "expected exactly one agent branch for $task, found ${#branches[@]}: ${branches[*]:-none}" >&2
  exit 2
}
branch=${branches[0]}

task_dir=$(git worktree list --porcelain | awk -v branch="refs/heads/$branch" '
  $1=="worktree" { path=$2 }
  $1=="branch" && $2==branch { print path }
')
[[ -n "$task_dir" ]] || { echo "no worktree found for $branch" >&2; exit 2; }

if [[ -n $(git -C "$task_dir" status --porcelain) ]]; then
  echo "task worktree is not clean: $task_dir" >&2
  exit 1
fi
python3 "$task_dir/tools/agents/verify-scope.py" "$task"

if [[ -n $(git -C "$integration_dir" status --porcelain) ]]; then
  echo "integration worktree is not clean: $integration_dir" >&2
  exit 1
fi

# Fail clearly if prerequisites were not merged. This repeats the wave gate for
# one-off task integration and prevents accidental out-of-order merges.
python3 - "$task" "$integration" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

task_id, integration = sys.argv[1:]
data = json.loads(Path('agents/task-dag.json').read_text())
item = next(task for task in data['tasks'] if task['id'] == task_id)
for dependency in item['dependsOn']:
    if dependency == 'BASE_MVP_PASS':
        continue
    refs = subprocess.run(
        ['git', 'for-each-ref', '--format=%(refname:short)', f'refs/heads/agent/{dependency}-*'],
        text=True,
        check=True,
        capture_output=True,
    ).stdout.splitlines()
    if len(refs) != 1:
        raise SystemExit(f'{task_id}: prerequisite {dependency} has {len(refs)} branches')
    merged = subprocess.run(
        ['git', 'merge-base', '--is-ancestor', refs[0], integration]
    ).returncode == 0
    if not merged:
        raise SystemExit(f'{task_id}: prerequisite {dependency} is not merged into {integration}')
PY

if git -C "$integration_dir" merge-base --is-ancestor "$branch" HEAD; then
  echo "$branch is already integrated"
  exit 0
fi

git -C "$integration_dir" merge --no-ff --no-edit "$branch"
make -C "$integration_dir" validate
printf 'integrated %s into %s at %s\n' "$branch" "$integration" "$(git -C "$integration_dir" rev-parse --short HEAD)"
