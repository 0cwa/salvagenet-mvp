#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"

for file in preflight.json qemu-command.json system.qcow2 data.raw seed.img AAVMF_CODE.fd AAVMF_VARS.fd; do
  [[ -f "$state/$file" ]] || { echo "missing $state/$file; run make qemu-lab-prepare" >&2; exit 2; }
done
if [[ -f "$state/qemu.pid" ]]; then
  pid=$(cat "$state/qemu.pid")
  if [[ $pid =~ ^[1-9][0-9]*$ ]] && kill -0 "$pid" 2>/dev/null; then
    echo "host-QEMU lab already running pid=$pid"
    exit 0
  fi
  rm -f "$state/qemu.pid"
fi
rm -f "$state/qmp.sock" "$state/qemu.stdout.log" "$state/qemu.stderr.log" "$state/serial.log"

command=()
while IFS= read -r -d '' argument; do
  command+=("$argument")
done < <(python3 - "$state/qemu-command.json" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
value = json.loads(path.read_text(encoding="utf-8"))
if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
    raise SystemExit("invalid qemu-command.json")
for item in value:
    sys.stdout.buffer.write(item.encode("utf-8") + b"\0")
PY
)
[[ ${#command[@]} -gt 0 ]] || { echo "empty QEMU command" >&2; exit 2; }

nohup "${command[@]}" </dev/null >"$state/qemu.stdout.log" 2>"$state/qemu.stderr.log" &
pid=$!
printf '%s\n' "$pid" > "$state/qemu.pid"
sleep 2
if ! kill -0 "$pid" 2>/dev/null; then
  echo "QEMU exited during launch" >&2
  tail -n 80 "$state/qemu.stderr.log" >&2 || true
  exit 1
fi
printf 'started canonical H02A host-QEMU lab pid=%s ssh=127.0.0.1:%s\n' "$pid" "$ssh_port"
