#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || cd "$(dirname "$0")/../.." && pwd)
while IFS= read -r -d '' file; do bash -n "$file"; done < <(find "$root" -type f -name '*.sh' -not -path '*/android/podroid/*' -not -path '*/.git/*' -print0)
if command -v shellcheck >/dev/null 2>&1; then
  mapfile -d '' files < <(find "$root" -type f -name '*.sh' -not -path '*/android/podroid/*' -not -path '*/.git/*' -print0)
  ((${#files[@]}==0)) || shellcheck -x "${files[@]}"
fi
echo 'shell syntax/lint OK'
