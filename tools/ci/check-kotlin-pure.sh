#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
if ! command -v kotlinc >/dev/null 2>&1; then
  echo 'pure Kotlin compile skipped (kotlinc not installed; Gradle covers it after Podroid import)'
  exit 0
fi
mapfile -t sources < <(
  find "$root/android/modules/node-model/src/main" "$root/android/modules/node-core/src/main" \
    -type f -name '*.kt' -print | sort
)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
kotlinc "${sources[@]}" -d "$tmp/domain.jar"
echo 'pure Kotlin domain/application compile OK'
