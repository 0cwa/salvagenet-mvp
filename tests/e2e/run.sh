#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
cd "$root"

# Always prove the complete decision/composition path without requiring Android hardware.
(
  cd android/podroid
  ./gradlew :node-shell:testDebugUnitTest --tests org.nodehost.shell.VerticalIntegrationTest
)
printf '%s\n' 'PASS-FAKE: enrollment -> distinct host/guest mesh credentials -> authenticated controller Ubuntu apply -> typed runtime reconciliation -> key-only bootstrap/recovery'

missing=()
[[ -x android/podroid/gradlew ]] || missing+=(podroid)
command -v adb >/dev/null 2>&1 || missing+=(adb)
[[ "$(adb get-state 2>/dev/null || true)" == device ]] || missing+=(authorized-device)
[[ -f lab/headscale/.env ]] || missing+=(headscale-env)
[[ -f controller/mvp-cli/controller.json ]] || missing+=(controller-config)
if ((${#missing[@]})); then
  printf 'BLOCKED-HARDWARE/SETUP: %s\n' "${missing[*]}"
  exit 77
fi

package_name=com.excp.podroid.debug
apk=android/podroid/app/build/outputs/apk/debug/app-debug.apk
[[ -f "$apk" ]] || { printf 'missing debug APK: %s\n' "$apk" >&2; exit 1; }
adb install -r "$apk"
adb shell am start-foreground-service -n "$package_name/org.nodehost.shell.NodeSupervisorService"
adb shell dumpsys package "$package_name" | grep -q 'org.nodehost.shell.NodeSupervisorService'
printf '%s\n' 'PASS-DEVICE-SMOKE: APK installed and NodeSupervisorService retained by Android'
printf '%s\n' 'Manual authorized lab continuation is required for VPN consent, live Headscale enrollment, ARM64 QEMU boot, guest mesh SSH, and recovery SSH.'
exit 77
