#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p secrets
chmod 700 secrets
staging=$(mktemp -d secrets/.mint.XXXXXX)
trap 'rm -rf "$staging"' EXIT

# Headscale 0.28 treats tagged devices as their own identity class, so these
# infrastructure keys deliberately have no user owner. Pin one use and a short
# expiry explicitly rather than relying on CLI defaults.
for pair in controller:node-controller host:node-host guest:node-worker; do
  name=${pair%%:*}
  tag=${pair##*:}
  key=$(./scripts/container.sh exec headscale preauthkeys create \
    --reusable=false --expiration 1h --tags "tag:$tag" | tr -d '\r\n')
  [[ "$key" =~ ^hskey-auth-[A-Za-z0-9_-]{32,128}$ ]] || {
    echo "Headscale returned an invalid pre-auth key for tag:$tag" >&2
    exit 1
  }
  printf '%s\n' "$key" > "$staging/$name.authkey"
  chmod 600 "$staging/$name.authkey"
  unset key
done

for name in controller host guest; do
  mv -f "$staging/$name.authkey" "secrets/$name.authkey"
done
rmdir "$staging"
trap - EXIT
printf 'created one-use keys under %s/secrets (contents not printed)\n' "$PWD"
