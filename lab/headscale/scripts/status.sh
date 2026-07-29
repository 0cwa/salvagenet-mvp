#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
url=$(awk -F= '$1=="HEADSCALE_PUBLIC_URL"{print $2}' .env)
: "${url:?HEADSCALE_PUBLIC_URL is missing from .env}"

# Bound startup polling so make lab-up is reliable without hiding a failed
# container behind an indefinite wait.
deadline=$((SECONDS + 60))
until curl --fail --silent --show-error --max-time 2 "$url/health" >/dev/null 2>&1; do
  if ((SECONDS >= deadline)); then
    echo "Headscale health did not pass within 60 seconds ($url)" >&2
    exit 1
  fi
  sleep 1
done
printf 'Headscale health: PASS (%s)\n' "$url"
./scripts/container.sh exec headscale nodes list
