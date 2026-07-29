#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/render-config.py >/dev/null
runtime=$(./scripts/runtime.sh)
if [[ "$runtime" == docker ]]; then
  docker compose --env-file .env -f compose.yaml run --rm headscale configtest
  docker compose --env-file .env -f compose.yaml up -d
else
  podman compose --env-file .env -f compose.yaml run --rm headscale configtest
  podman compose --env-file .env -f compose.yaml up -d
fi
./scripts/status.sh
