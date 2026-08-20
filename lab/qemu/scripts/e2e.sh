#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
status=FAIL
summary='host-QEMU laboratory failed'
cleanup(){
  local rc=$?
  trap - EXIT INT TERM
  if [[ $rc -eq 0 ]]; then
    status=PASS
    summary='Ubuntu UEFI, NoCloud and key-only SSH passed'
  fi
  python3 "$(dirname "$0")/report.py" --state "$state" --status "$status" --started-at "$started" --summary "$summary" || true
  "$(dirname "$0")/stop.sh" >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
"$(dirname "$0")/stop.sh" >/dev/null 2>&1 || true
rm -f "$state/system.qcow2" "$state/seed.img" "$state/AAVMF_CODE.fd" "$state/AAVMF_VARS.fd" \
  "$state/qmp.sock" "$state/qemu.pid" "$state/serial.log" "$state/qemu.stdout.log" "$state/qemu.stderr.log"
"$(dirname "$0")/prepare.sh"
"$(dirname "$0")/start.sh"
"$(dirname "$0")/smoke.sh"
