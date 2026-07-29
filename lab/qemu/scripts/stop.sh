#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"
if [[ ! -f "$state/qemu.pid" ]]; then
  echo "host-QEMU lab is not running"
  exit 0
fi
pid=$(cat "$state/qemu.pid")
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  for _ in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
  kill -0 "$pid" 2>/dev/null && kill -9 "$pid"
fi
rm -f "$state/qemu.pid" "$state/qmp.sock"
printf 'stopped host-QEMU lab\n'
