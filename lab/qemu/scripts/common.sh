#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../../.." && pwd))
raw_state=${NODEHOST_QEMU_LAB_DIR:-$root/.local/qemu-lab}
ssh_port=${NODEHOST_QEMU_LAB_SSH_PORT:-2222}

state=$(python3 - "$root" "$raw_state" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve(strict=True)
local = root / '.local'
local.mkdir(mode=0o700, exist_ok=True)
if local.is_symlink():
    raise SystemExit('repository .local directory must not be a symlink')
candidate = Path(sys.argv[2]).expanduser()
if not candidate.is_absolute():
    candidate = Path.cwd() / candidate
if candidate.is_symlink():
    raise SystemExit('H02A state directory must not be a symlink')
resolved = candidate.resolve(strict=False)
try:
    relative = resolved.relative_to(local.resolve(strict=True))
except ValueError:
    raise SystemExit(f'H02A state directory must remain under {local}')
if not relative.parts:
    raise SystemExit('H02A state directory cannot be the repository .local root')
print(resolved)
PY
)

[[ $ssh_port =~ ^[0-9]+$ ]] && (( ssh_port >= 1024 && ssh_port <= 65535 )) || {
  echo "NODEHOST_QEMU_LAB_SSH_PORT must be in 1024..65535" >&2
  exit 2
}
mkdir -p "$state"
chmod 0700 "$state"
known_hosts="$state/known_hosts"
touch "$known_hosts"
chmod 0600 "$known_hosts"
export root state ssh_port known_hosts

ssh_options=(
  -F /dev/null
  -q
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=accept-new
  -o UserKnownHostsFile="$known_hosts"
  -o GlobalKnownHostsFile=/dev/null
  -o ConnectTimeout=5
  -o ConnectionAttempts=1
  -i "$state/id_ed25519"
  -p "$ssh_port"
)

ssh_nodeadmin() {
  local timeout_seconds=$1
  shift
  timeout "$timeout_seconds" ssh "${ssh_options[@]}" nodeadmin@127.0.0.1 "$@"
}

ssh_root() {
  local timeout_seconds=$1
  shift
  timeout "$timeout_seconds" ssh "${ssh_options[@]}" root@127.0.0.1 "$@"
}

wait_for_ssh() {
  local timeout_seconds=${1:-300}
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if ssh_nodeadmin 8 true >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "SSH did not become ready within ${timeout_seconds}s" >&2
  return 1
}

wait_for_ssh_down() {
  local timeout_seconds=${1:-90}
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if ! ssh_nodeadmin 5 true >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "SSH did not become unavailable within ${timeout_seconds}s" >&2
  return 1
}

read_qemu_pid() {
  [[ -f "$state/qemu.pid" && ! -L "$state/qemu.pid" ]] || return 1
  local pid
  pid=$(cat "$state/qemu.pid")
  [[ $pid =~ ^[1-9][0-9]*$ ]] || return 1
  printf '%s\n' "$pid"
}

qemu_running() {
  local pid
  pid=$(read_qemu_pid) || return 1
  kill -0 "$pid" 2>/dev/null
}

wait_for_qemu_exit() {
  local timeout_seconds=${1:-180}
  local deadline=$((SECONDS + timeout_seconds))
  local pid
  pid=$(read_qemu_pid) || {
    rm -f "$state/qemu.pid" "$state/qmp.sock"
    return 0
  }
  while (( SECONDS < deadline )); do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$state/qemu.pid" "$state/qmp.sock"
      return 0
    fi
    sleep 1
  done
  echo "QEMU pid $pid did not exit within ${timeout_seconds}s" >&2
  return 1
}

snapshot_qemu_logs() {
  local stage=$1
  [[ $stage =~ ^(initial|guest-reboot|qemu-restart)$ ]] || {
    echo "invalid H02A evidence stage: $stage" >&2
    return 2
  }
  local name source target
  for name in serial qemu.stdout qemu.stderr; do
    source="$state/$name.log"
    target="$state/$name-$stage.log"
    if [[ -f $source && ! -L $source ]]; then
      cp --reflink=auto --sparse=always "$source" "$target"
      chmod 0600 "$target"
    fi
  done
}
