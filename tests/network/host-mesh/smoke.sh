#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
lock="$repo_root/android/vendor/tailscale/tailscale.lock"
aar="$repo_root/android/vendor/tailscale/build/libtailscale.aar"
mesh_aar="$repo_root/android/modules/mesh-tailscale/build/outputs/aar/mesh-tailscale-release.aar"
apk="$repo_root/android/podroid/app/build/outputs/apk/debug/app-debug.apk"

python3 - "$lock" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    lock = json.load(f)
assert len(lock["commit"]) == 40 and "VERIFY" not in lock["commit"]
assert len(lock["coreCommit"]) == 40
PY
[[ -s "$aar" ]] || { echo "FAIL: build the pinned libtailscale AAR first" >&2; exit 1; }
unzip -tqq "$aar"
tmp_classes="$(mktemp)"
trap 'rm -f "$tmp_classes"' EXIT
unzip -p "$aar" classes.jar >"$tmp_classes"
unzip -Z1 "$tmp_classes" | grep -qx 'libtailscale/Libtailscale.class' || {
  echo "FAIL: generated AAR does not contain official libtailscale binding" >&2
  exit 1
}
[[ -s "$mesh_aar" ]] || { echo "FAIL: assemble the mesh-tailscale release AAR first" >&2; exit 1; }
unzip -Z1 "$mesh_aar" | grep -qx 'libs/libtailscale.jar' || {
  echo "FAIL: mesh AAR does not embed the generated binding JAR" >&2
  exit 1
}
unzip -Z1 "$mesh_aar" | grep -qx 'jni/arm64-v8a/libgojni.so' || {
  echo "FAIL: mesh AAR does not package the generated ARM64 JNI library" >&2
  exit 1
}
if [[ ! -s "$apk" ]]; then
  echo "SKIP: official binding checks passed, but no assembled debug APK is available"
  exit 77
fi

unzip -Z1 "$apk" | grep -x 'lib/arm64-v8a/libgojni.so' >/dev/null || {
  echo "FAIL: app APK does not package the generated ARM64 JNI library" >&2
  exit 1
}

if ! command -v adb >/dev/null 2>&1; then
  echo "SKIP: adb is unavailable; static official-binding checks passed"
  exit 77
fi
device="$(adb devices | awk 'NR>1 && $2 == "device" {print $1; exit}')"
if [[ -z "$device" ]]; then
  echo "SKIP: no authorized Android device; static official-binding checks passed"
  exit 77
fi
if [[ "$(adb -s "$device" shell getprop ro.kernel.qemu | tr -d '\r')" == "1" ]]; then
  echo "SKIP: an emulator is connected, but T05 requires physical-device VPN evidence"
  exit 77
fi

adb -s "$device" install -r "$apk" >/dev/null
adb -s "$device" shell dumpsys package com.excp.podroid.debug | grep -q 'NodeTailscaleVpnService' || {
  echo "FAIL: installed APK does not declare NodeTailscaleVpnService" >&2
  exit 1
}

# VPN consent cannot be granted safely through adb. The composition owner must
# import enrollment and call HostMesh before this task can observe a live node.
echo "SKIP: APK installed and service verified; interactive VPN approval and imported enrollment are required"
exit 77
