#!/usr/bin/env bash
set -euo pipefail

: "${ANDROID_SDK_ROOT:?source ~/.config/nodehost/env.sh first}"
name=${NODEHOST_AVD_NAME:-nodehost-api36}
state_dir=${NODEHOST_EMULATOR_STATE_DIR:-.local/emulator}
mkdir -p "$state_dir"
if adb devices | awk 'NR>1 && $1 ~ /^emulator-/ && $2=="device" {found=1} END{exit !found}'; then
  echo "an Android emulator is already running" >&2
  exit 0
fi

accel=()
if [[ -r /dev/kvm && -w /dev/kvm ]]; then
  accel=(-accel on)
else
  echo "WARN: /dev/kvm unavailable; emulator may be very slow" >&2
  accel=(-accel auto)
fi

nohup "$ANDROID_SDK_ROOT/emulator/emulator" "@$name" \
  -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect \
  -no-snapshot-save -wipe-data "${accel[@]}" \
  >"$state_dir/emulator.log" 2>&1 &
echo $! > "$state_dir/emulator.pid"
adb wait-for-device
for _ in $(seq 1 180); do
  [[ $(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r') == 1 ]] && {
    echo "emulator $name booted"
    exit 0
  }
  sleep 1
done
echo "emulator did not complete boot; see $state_dir/emulator.log" >&2
exit 1
