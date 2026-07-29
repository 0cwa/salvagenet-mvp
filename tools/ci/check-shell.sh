#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
while IFS= read -r -d '' file; do bash -n "$file"; done < <(find "$root" -type f -name '*.sh' -not -path '*/android/podroid/*' -not -path '*/.git/*' -print0)
# In command substitution, `a || b && c` is parsed as `(a || b) && c` and
# can emit two repository paths when `a` succeeds. Require a subshell around
# fallback `cd && pwd` expressions.
if grep -RIn --include='*.sh' --exclude-dir=.git --exclude-dir=podroid \
    -E 'git rev-parse --show-toplevel.*\|\|[[:space:]]+cd .*&&[[:space:]]+pwd' "$root"; then
  echo 'ambiguous repository-root fallback; wrap (cd ... && pwd) in a subshell' >&2
  exit 1
fi
if command -v shellcheck >/dev/null 2>&1; then
  mapfile -d '' files < <(find "$root" -type f -name '*.sh' -not -path '*/android/podroid/*' -not -path '*/.git/*' -print0)
  ((${#files[@]}==0)) || shellcheck -x "${files[@]}"
fi
echo 'shell syntax/lint OK'
