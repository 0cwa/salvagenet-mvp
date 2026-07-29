#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel); cd "$root"
commit=$(python3 -c 'import json;print(json.load(open("android/vendor/tailscale/tailscale.lock"))["commit"])')
[[ "$commit" != VERIFY-* ]] || { echo "run tools/vendor/pin-tailscale.sh first" >&2; exit 2; }
dest=android/vendor/tailscale/upstream
[[ ! -e "$dest" ]] || { echo "$dest already exists" >&2; exit 2; }
git clone --no-checkout https://github.com/tailscale/tailscale-android.git "$dest"
git -C "$dest" checkout --detach "$commit"
printf 'T05 must retain only required libtailscale/platform source and provenance; do not commit .git.
'
