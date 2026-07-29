#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
cd "$root"
missing=()
[[ -x android/podroid/gradlew ]] || missing+=(podroid)
command -v adb >/dev/null 2>&1 || missing+=(adb)
[[ "$(adb get-state 2>/dev/null || true)" == device ]] || missing+=(authorized-device)
[[ -f lab/headscale/.env ]] || missing+=(headscale-env)
[[ -f controller/mvp-cli/controller.json ]] || missing+=(controller-config)
if ((${#missing[@]})); then
  printf 'BLOCKED-HARDWARE/SETUP: %s
' "${missing[*]}"
  exit 77
fi
printf 'E2E harness prerequisites present. T07 replaces this scaffold marker with the vertical scenario.
'
exit 77
