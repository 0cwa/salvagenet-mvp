#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || cd "$(dirname "$0")/../.." && pwd)
cd "$root"

required=(git bash python3 java javac curl jq make unzip zip openssl)
optional=(docker podman adb sdkmanager go shellcheck shfmt yamllint mise git-lfs qemu-system-aarch64 qemu-img)
failed=0

for cmd in "${required[@]}"; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf 'PASS  %-22s %s\n' "$cmd" "$(command -v "$cmd")"
  else
    printf 'FAIL  %-22s missing\n' "$cmd"
    failed=1
  fi
done
for cmd in "${optional[@]}"; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf 'INFO  %-22s %s\n' "$cmd" "$(command -v "$cmd")"
  else
    printf 'WARN  %-22s missing/optional until its task\n' "$cmd"
  fi
done

java_major=$(java -version 2>&1 | awk -F'[".]' '/version/ {print $2; exit}')
if [[ "$java_major" == 17 ]]; then
  echo 'PASS  JDK 17 selected'
else
  echo "WARN  active JDK is ${java_major:-unknown}; imported Android build requires JDK 17"
fi

python3 - <<'PY'
import sys
ok=sys.version_info >= (3, 12)
print(('PASS' if ok else 'WARN') + f'  Python {sys.version.split()[0]} (3.12+ recommended)')
PY

if command -v go >/dev/null 2>&1; then
  go_version=$(go env GOVERSION 2>/dev/null || true)
  if [[ "$go_version" == go1.26.3 ]]; then
    echo 'PASS  Go 1.26.3 selected for Tailscale v1.98.2 baseline'
  else
    echo "WARN  active Go is ${go_version:-unknown}; T05 baseline expects Go 1.26.3"
  fi
else
  echo 'WARN  Go missing; required before T05 embedded Tailscale work'
fi

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    echo 'PASS  Docker daemon authorized'
  else
    echo 'WARN  Docker installed but daemon/current-user authorization is unavailable'
  fi
elif command -v podman >/dev/null 2>&1; then
  podman info >/dev/null 2>&1 && echo 'PASS  Podman authorized' || echo 'WARN  Podman unavailable to current user'
fi

if command -v adb >/dev/null 2>&1; then
  state=$(adb get-state 2>/dev/null || true)
  [[ "$state" == device ]] && echo 'PASS  ADB device authorized' || echo 'WARN  ADB has no authorized device'
fi


if [[ -e /dev/kvm ]]; then
  if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    echo 'PASS  /dev/kvm authorized for Android emulator'
  else
    echo 'WARN  /dev/kvm exists but current user lacks access'
  fi
else
  echo 'INFO  /dev/kvm absent; physical-device tests remain available'
fi

if [[ -x android/podroid/gradlew ]]; then
  echo 'PASS  Podroid imported'
else
  echo 'INFO  Podroid not imported (expected for the clean scaffold)'
fi

if [[ -n "${ANDROID_SDK_ROOT:-}" && -d "${ANDROID_SDK_ROOT}" ]]; then
  echo "PASS  ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT"
  for path in \
    "platforms/android-36" \
    "build-tools/36.0.0" \
    "ndk/27.2.12479018" \
    "platform-tools/adb"; do
    [[ -e "$ANDROID_SDK_ROOT/$path" ]] && echo "PASS  SDK component $path" || echo "WARN  SDK component missing: $path"
  done
else
  echo 'WARN  ANDROID_SDK_ROOT unset or missing'
fi

free_gib=$(df -Pk "$root" | awk 'NR==2 {printf "%d", $4/1024/1024}')
if (( free_gib >= 30 )); then
  echo "PASS  working filesystem has ${free_gib} GiB free"
else
  echo "WARN  only ${free_gib} GiB free; Podroid native/image builds may exhaust storage"
fi

exit "$failed"
