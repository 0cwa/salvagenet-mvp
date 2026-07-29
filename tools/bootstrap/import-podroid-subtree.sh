#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
lock=android/upstream/podroid.lock
repo=$(python3 -c 'import json;print(json.load(open("android/upstream/podroid.lock"))["repository"])')
commit=$(python3 -c 'import json;print(json.load(open("android/upstream/podroid.lock"))["commit"])')
dest=android/podroid
if [[ -d "$dest/.git" || -f "$dest/settings.gradle.kts" ]]; then
  echo "$dest already exists; refusing to overwrite" >&2; exit 2
fi
git diff --quiet && git diff --cached --quiet || { echo "working tree must be clean" >&2; exit 2; }
git subtree add --prefix="$dest" "$repo" "$commit" --squash
printf 'Imported Podroid %s at %s
' "$commit" "$dest"
