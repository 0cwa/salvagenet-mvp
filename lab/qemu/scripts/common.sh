#!/usr/bin/env bash
set -euo pipefail
umask 077

root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../../.." && pwd))
raw_state=${NODEHOST_QEMU_LAB_DIR:-$root/.local/qemu-lab}
ssh_port=${NODEHOST_QEMU_LAB_SSH_PORT:-2222}
readonly ssh_wait_seconds=900
readonly cloud_init_wait_seconds=1800

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

if [[ ! $ssh_port =~ ^[1-9][0-9]*$ ]]; then
  echo "NODEHOST_QEMU_LAB_SSH_PORT must be one canonical decimal integer" >&2
  exit 2
fi
ssh_port=$((10#$ssh_port))
if (( ssh_port < 1024 || ssh_port > 65535 )); then
  echo "NODEHOST_QEMU_LAB_SSH_PORT must be in 1024..65535" >&2
  exit 2
fi
mkdir -p "$state"
chmod 0700 "$state"
known_hosts="$state/known_hosts"
touch "$known_hosts"
chmod 0600 "$known_hosts"
export root state ssh_port known_hosts ssh_wait_seconds cloud_init_wait_seconds

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

ssh_single_method() {
  local method=$1 timeout_seconds=$2
  local password=no keyboard=no
  case "$method" in
    password) password=yes ;;
    keyboard-interactive) keyboard=yes ;;
    *) echo "unsupported SSH probe method: $method" >&2; return 2 ;;
  esac
  timeout "$timeout_seconds" ssh \
    -F /dev/null \
    -q \
    -o BatchMode=yes \
    -o IdentitiesOnly=yes \
    -o PubkeyAuthentication=no \
    -o PasswordAuthentication="$password" \
    -o KbdInteractiveAuthentication="$keyboard" \
    -o PreferredAuthentications="$method" \
    -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile="$known_hosts" \
    -o GlobalKnownHostsFile=/dev/null \
    -o ConnectTimeout=5 \
    -o ConnectionAttempts=1 \
    -p "$ssh_port" \
    nodeadmin@127.0.0.1 true
}

wait_for_ssh() {
  local timeout_seconds=${1:-$ssh_wait_seconds}
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

wait_for_boot_id_change() {
  local previous=$1 timeout_seconds=${2:-$ssh_wait_seconds}
  local deadline=$((SECONDS + timeout_seconds)) current
  while (( SECONDS < deadline )); do
    current=$(ssh_nodeadmin 15 'cat /proc/sys/kernel/random/boot_id' 2>/dev/null || true)
    if [[ $current =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ && $current != "$previous" ]]; then
      printf '%s
' "$current"
      return 0
    fi
    sleep 2
  done
  echo "guest boot ID did not change within ${timeout_seconds}s" >&2
  return 1
}

read_qemu_pid() {
  [[ -f "$state/qemu.pid" && ! -L "$state/qemu.pid" ]] || return 1
  local pid
  pid=$(cat "$state/qemu.pid")
  [[ $pid =~ ^[1-9][0-9]*$ ]] || return 1
  printf '%s\n' "$pid"
}

qemu_pid_matches() {
  local pid=$1
  python3 - "$pid" "$state" <<'PY' >/dev/null 2>&1
from pathlib import Path
import sys
pid = sys.argv[1]
state = Path(sys.argv[2])
try:
    raw = Path(f'/proc/{pid}/cmdline').read_bytes()
except OSError:
    raise SystemExit(1)
args = [value.decode('utf-8', 'surrogateescape') for value in raw.split(b'\0') if value]
if not args or Path(args[0]).name != 'qemu-system-aarch64':
    raise SystemExit(1)
try:
    name_index = args.index('-name')
except ValueError:
    raise SystemExit(1)
if name_index + 1 >= len(args) or args[name_index + 1] != 'nodehost-h02a':
    raise SystemExit(1)
if not any(str(state / 'system.qcow2') in value for value in args):
    raise SystemExit(1)
if not any(str(state / 'qmp.sock') in value for value in args):
    raise SystemExit(1)
PY
}

live_qemu_pid() {
  local pid
  pid=$(read_qemu_pid) || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  if ! qemu_pid_matches "$pid"; then
    echo "refusing to treat pid $pid as H02A QEMU: process identity differs" >&2
    return 2
  fi
  printf '%s\n' "$pid"
}

qemu_running() {
  live_qemu_pid >/dev/null 2>&1
}

wait_for_qemu_exit() {
  local timeout_seconds=${1:-180}
  local deadline=$((SECONDS + timeout_seconds))
  local pid
  pid=$(read_qemu_pid) || {
    rm -f "$state/qemu.pid" "$state/qmp.sock"
    return 0
  }
  if kill -0 "$pid" 2>/dev/null && ! qemu_pid_matches "$pid"; then
    echo "refusing to wait on pid $pid: process identity differs from H02A QEMU" >&2
    return 2
  fi
  while (( SECONDS < deadline )); do
    if ! kill -0 "$pid" 2>/dev/null || ! qemu_pid_matches "$pid"; then
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
    [[ -f $source && ! -L $source ]] || {
      echo "required QEMU log is missing or unsafe: $source" >&2
      return 1
    }
    cp --reflink=auto --sparse=always "$source" "$target"
    chmod 0600 "$target"
  done
}
