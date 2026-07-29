#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/down.sh 2>/dev/null || true
rm -rf data secrets config/generated
printf 'lab state removed
'
