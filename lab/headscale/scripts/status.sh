#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."; runtime=$(./scripts/runtime.sh)
url=$(awk -F= '$1=="HEADSCALE_PUBLIC_URL"{print $2}' .env)
curl --fail --silent --show-error "$url/health" >/dev/null
printf 'Headscale health: PASS (%s)
' "$url"
if [[ "$runtime" == docker ]]; then
  docker compose --env-file .env -f compose.yaml exec -T headscale headscale nodes list
else
  podman compose --env-file .env -f compose.yaml exec -T headscale headscale nodes list
fi
