#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
runtime=$(./scripts/runtime.sh)
mkdir -p secrets
chmod 700 secrets

compose() {
  if [[ "$runtime" == docker ]]; then
    docker compose --env-file .env -f compose.yaml "$@"
  else
    podman compose --env-file .env -f compose.yaml "$@"
  fi
}

# Headscale 0.28 treats tagged devices as their own identity class, so these
# infrastructure keys deliberately have no user owner. Defaults are one use
# and one hour; tests must never make them reusable merely for convenience.

for pair in controller:node-controller host:node-host guest:node-worker; do
  name=${pair%%:*}
  tag=${pair##*:}
  key=$(compose exec -T headscale \
    headscale preauthkeys create --tags "tag:$tag" | tr -d '\r\n')
  [[ -n "$key" ]] || {
    echo "Headscale returned an empty pre-auth key for tag:$tag" >&2
    exit 1
  }
  printf '%s\n' "$key" > "secrets/$name.authkey"
  chmod 600 "secrets/$name.authkey"
  unset key
done

printf 'created one-use keys under %s/secrets (contents not printed)\n' "$PWD"
