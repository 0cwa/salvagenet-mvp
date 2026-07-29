#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."; runtime=$(./scripts/runtime.sh)
mkdir -p secrets; chmod 700 secrets
compose(){ if [[ "$runtime" == docker ]]; then docker compose --env-file .env -f compose.yaml "$@"; else podman compose --env-file .env -f compose.yaml "$@"; fi; }
compose exec -T headscale headscale users create lab >/dev/null 2>&1 || true
for pair in controller:node-controller host:node-host guest:node-worker; do
  name=${pair%%:*}; tag=${pair##*:}
  compose exec -T headscale headscale preauthkeys create --tags "tag:$tag" | tr -d '
' > "secrets/$name.authkey"
  chmod 600 "secrets/$name.authkey"
done
printf 'created one-use keys under %s/secrets (contents not printed)
' "$PWD"
