#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"

for file in preflight.json qemu-command.json system.qcow2 data.raw seed.img AAVMF_CODE.fd AAVMF_VARS.fd; do
  [[ -f "$state/$file" && ! -L "$state/$file" ]] || {
    echo "missing or unsafe $state/$file; run make qemu-lab-prepare" >&2
    exit 2
  }
done
if [[ -e "$state/qemu.pid" ]]; then
  pid=$(read_qemu_pid) || {
    echo "invalid H02A QEMU pid file" >&2
    exit 2
  }
  if kill -0 "$pid" 2>/dev/null; then
    qemu_pid_matches "$pid" || {
      echo "refusing to reuse pid $pid: process identity differs from H02A QEMU" >&2
      exit 2
    }
    echo "host-QEMU lab already running pid=$pid"
    exit 0
  fi
  rm -f "$state/qemu.pid"
fi
rm -f "$state/qmp.sock" "$state/qemu.stdout.log" "$state/qemu.stderr.log" "$state/serial.log"

command=()
while IFS= read -r -d '' argument; do
  command+=("$argument")
done < <(python3 - "$state/qemu-command.json" "$state/preflight.json" "$state" <<'PY'
from pathlib import Path
import json
import os
import sys
command_path = Path(sys.argv[1])
preflight_path = Path(sys.argv[2])
state = Path(sys.argv[3])
command = json.loads(command_path.read_text(encoding='utf-8'))
preflight = json.loads(preflight_path.read_text(encoding='utf-8'))
if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
    raise SystemExit('invalid qemu-command.json')
if any('\x00' in item or '\n' in item or '\r' in item for item in command):
    raise SystemExit('QEMU command contains a forbidden control character')
if Path(command[0]).name != 'qemu-system-aarch64' or not os.access(command[0], os.X_OK):
    raise SystemExit('QEMU executable is missing or unexpected')
try:
    recorded = preflight['lab']['qemuCommand']
except (KeyError, TypeError):
    raise SystemExit('preflight has no recorded QEMU command')
normalized = [item.replace(str(state), '$STATE') for item in command]
if normalized != recorded:
    raise SystemExit('qemu-command.json differs from the recorded preflight command')
for item in command:
    sys.stdout.buffer.write(item.encode('utf-8') + b'\0')
PY
)
[[ ${#command[@]} -gt 0 ]] || { echo "empty QEMU command" >&2; exit 2; }

nohup "${command[@]}" </dev/null >"$state/qemu.stdout.log" 2>"$state/qemu.stderr.log" &
pid=$!
printf '%s\n' "$pid" > "$state/qemu.pid.tmp"
chmod 0600 "$state/qemu.pid.tmp"
mv "$state/qemu.pid.tmp" "$state/qemu.pid"
sleep 2
if ! kill -0 "$pid" 2>/dev/null || ! qemu_pid_matches "$pid"; then
  echo "QEMU exited during launch or its process identity differs" >&2
  tail -n 80 "$state/qemu.stderr.log" >&2 || true
  rm -f "$state/qemu.pid" "$state/qmp.sock"
  exit 1
fi
printf 'started canonical H02A host-QEMU lab pid=%s ssh=127.0.0.1:%s\n' "$pid" "$ssh_port"
