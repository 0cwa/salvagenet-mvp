#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$root"
failed=0
check(){ if "$@" >/dev/null 2>&1; then printf 'PASS  %s\n' "$*"; else printf 'FAIL  %s\n' "$*"; failed=1; fi; }
check tools/ci/check.sh
if command -v go >/dev/null 2>&1 && [[ $(go env GOVERSION 2>/dev/null || true) == go1.26.3 ]]; then
  printf 'PASS  Go 1.26.3 selected for embedded Tailscale\n'
else
  printf 'FAIL  Go 1.26.3 missing; run tools/bootstrap/install-go.sh and source ~/.config/nodehost/env.sh\n'
  failed=1
fi
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  check git diff --quiet
  check git diff --cached --quiet
fi
if [[ -x android/podroid/gradlew ]]; then
  check test -f android/podroid/settings.gradle.kts
else
  printf 'WARN  Podroid not imported; T00 must run before Android tasks\n'
fi
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  printf 'PASS  Docker authorized\n'
elif command -v podman >/dev/null 2>&1; then
  printf 'PASS  Podman available\n'
else
  printf 'WARN  no authorized container runtime; Headscale/native builds blocked\n'
fi
if command -v adb >/dev/null 2>&1; then
  state=$(adb get-state 2>/dev/null || true)
  [[ "$state" == device ]] && printf 'PASS  ADB device authorized\n' || printf 'WARN  no authorized ADB device\n'
else
  printf 'WARN  adb missing\n'
fi
exit "$failed"
