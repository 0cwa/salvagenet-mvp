#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."; runtime=$(./scripts/runtime.sh)
if [[ "$runtime" == docker ]]; then
  docker compose --env-file .env -f compose.yaml down
else
  podman compose --env-file .env -f compose.yaml down
fi
