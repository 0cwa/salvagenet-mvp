#!/usr/bin/env bash
set -euo pipefail

# Graceful counterpart to start-nodehost-dev-with-usb.sh. It never uses
# virsh destroy and never changes ADB state.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
reconciler=$script_dir/reconcile-usb-device.sh
config_file=${SALVAGEHOST_USB_CONFIG:-/etc/salvagehost/nodehost-dev-usb.conf}
monitor_service=salvagehost-usb-reconcile.service

usage() {
  cat >&2 <<'EOF'
usage: stop-nodehost-dev-with-usb.sh [--config FILE]

Requires root. It requests a bounded graceful shutdown, then stops the
event monitor and removes the transient udev rule/session. A timeout leaves
the VM and USB session running so qemu does not lose its device unexpectedly.
EOF
}

while (($#)); do
  case $1 in
    --config)
      (($# >= 2)) || { usage; exit 2; }
      config_file=$2
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

"$reconciler" --validate-config --config "$config_file" >/dev/null
[[ $EUID -eq 0 ]] || { echo "stop-nodehost-dev: requires root" >&2; exit 2; }
command -v virsh >/dev/null || { echo "stop-nodehost-dev: virsh is required" >&2; exit 1; }
command -v systemctl >/dev/null || { echo "stop-nodehost-dev: systemctl is required" >&2; exit 1; }
command -v flock >/dev/null || { echo "stop-nodehost-dev: flock is required" >&2; exit 1; }

session_lock=/run/lock/salvagehost-nodehost-dev-usb-session.lock
mkdir -p -- "$(dirname -- "$session_lock")"
exec 8>"$session_lock"
flock -n 8 || { echo "stop-nodehost-dev: another VM USB lifecycle operation is running" >&2; exit 1; }

timeout_sec=$(awk -F= '$1 == "SALVAGEHOST_USB_STOP_TIMEOUT_SEC" { print $2 }' "$config_file")
[[ $timeout_sec =~ ^[1-9][0-9]*$ ]] || { echo "stop-nodehost-dev: invalid stop timeout" >&2; exit 2; }

state=$(virsh -c qemu:///system domstate nodehost-dev | tr -d '\r' | head -n 1)
case $state in
  running)
    virsh -c qemu:///system shutdown nodehost-dev >/dev/null
    for ((elapsed = 0; elapsed < timeout_sec; elapsed++)); do
      sleep 1
      state=$(virsh -c qemu:///system domstate nodehost-dev | tr -d '\r' | head -n 1)
      [[ $state == 'shut off' ]] && break
    done
    [[ $state == 'shut off' ]] || {
      echo "stop-nodehost-dev: graceful shutdown timed out; VM and USB session remain active" >&2
      exit 1
    }
    ;;
  'shut off'|crashed)
    ;;
  *)
    echo "stop-nodehost-dev: refusing VM state $state" >&2
    exit 1
    ;;
esac

systemctl stop "$monitor_service" >/dev/null 2>&1 || true
"$reconciler" --cleanup-session --config "$config_file"
echo "nodehost-dev is stopped and the transient USB session is inactive"
