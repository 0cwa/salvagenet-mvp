#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 ]] || { echo "usage: $0 <task-id>" >&2; exit 2; }
exec "$(dirname "$0")/create-worktree.sh" "$1"
