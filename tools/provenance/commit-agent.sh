#!/usr/bin/env bash
set -euo pipefail
usage() {
  echo "usage: AGENT_MODEL=... AGENT_RUN_ID=... AGENT_TASK_ID=Txx $0 <commit message>" >&2
  exit 2
}
[[ $# -ge 1 ]] || usage
: "${AGENT_MODEL:?set AGENT_MODEL}"
: "${AGENT_RUN_ID:?set AGENT_RUN_ID}"
: "${AGENT_TASK_ID:?set AGENT_TASK_ID}"
mode=${AGENT_MODE:-goal}
message=$*
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
cat > "$tmp" <<EOF
$message

Agent-Model: $AGENT_MODEL
Agent-Run-ID: $AGENT_RUN_ID
Agent-Task-ID: $AGENT_TASK_ID
Agent-Mode: $mode
EOF
git commit -F "$tmp"
