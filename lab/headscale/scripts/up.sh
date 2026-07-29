#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/render-config.py >/dev/null
./scripts/container.sh configtest
./scripts/container.sh up
./scripts/status.sh
