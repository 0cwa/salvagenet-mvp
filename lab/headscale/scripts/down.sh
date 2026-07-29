#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."; runtime=$(./scripts/runtime.sh)
[[ "$runtime" == docker ]] && docker compose --env-file .env -f compose.yaml down || podman compose --env-file .env -f compose.yaml down
