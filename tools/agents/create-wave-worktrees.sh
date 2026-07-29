#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 ]] || { echo "usage: $0 <wave>" >&2; exit 2; }
exec python3 "$(dirname "$0")/create-wave-worktrees.py" "$1"
