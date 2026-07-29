#!/usr/bin/env bash
set -euo pipefail
serial=$(adb devices | awk 'NR>1 && $1 ~ /^emulator-/ && $2=="device" {print $1; exit}')
if [[ -z "$serial" ]]; then
  echo "no running emulator"
  exit 0
fi
adb -s "$serial" emu kill >/dev/null
printf 'stopped %s\n' "$serial"
