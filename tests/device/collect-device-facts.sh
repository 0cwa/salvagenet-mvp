#!/usr/bin/env bash
set -euo pipefail

command -v adb >/dev/null || { echo "adb missing" >&2; exit 1; }
[[ "$(adb get-state 2>/dev/null || true)" == device ]] || {
  echo "no authorized adb device" >&2
  exit 1
}

root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
out="$root/.local/device-facts/$(date -u +%Y%m%dT%H%M%SZ).txt"
mkdir -p "$(dirname "$out")"

{
  echo "serial=$(adb get-serialno)"
  for prop in \
    ro.product.manufacturer \
    ro.product.model \
    ro.build.version.release \
    ro.build.version.sdk \
    ro.product.cpu.abi \
    ro.build.version.security_patch \
    ro.boot.verifiedbootstate \
    ro.boot.flash.locked; do
    value=$(adb shell getprop "$prop" | tr -d '\r\n')
    printf '%s=%s\n' "$prop" "$value"
  done

  page_size=$(adb shell getconf PAGESIZE 2>/dev/null | tr -d '\r\n')
  printf 'page_size=%s\n' "$page_size"
  adb shell cat /proc/meminfo | head -5
  adb shell df -h /data | tail -1
  adb shell dumpsys battery | sed -n '1,25p'
} > "$out"

printf '%s\n' "$out"
