#!/usr/bin/env bash
set -euo pipefail

# The only supported start boundary for the physical HIL phone.  Runtime USB
# permissions, the session marker, the event monitor, and the live hostdev are
# all created here and are never enabled by a timer or persistent udev rule.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
reconciler=$script_dir/reconcile-usb-device.sh
config_file=${SALVAGEHOST_USB_CONFIG:-/etc/salvagehost/nodehost-dev-usb.conf}
session_dir=/run/salvagehost
monitor_service=salvagehost-usb-reconcile.service

usage() {
  cat >&2 <<'EOF'
usage: start-nodehost-dev-with-usb.sh [--config FILE]

Requires root. It activates the exact phone's transient udev rule, removes any
matching persistent libvirt hostdev, starts the VM, and attaches the current
USB address with --live. Re-enumeration is handled by the event monitor.
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
[[ $EUID -eq 0 ]] || { echo "start-nodehost-dev: requires root" >&2; exit 2; }
command -v virsh >/dev/null || { echo "start-nodehost-dev: virsh is required" >&2; exit 1; }
command -v systemctl >/dev/null || { echo "start-nodehost-dev: systemctl is required" >&2; exit 1; }
command -v flock >/dev/null || { echo "start-nodehost-dev: flock is required" >&2; exit 1; }

session_lock=/run/lock/salvagehost-nodehost-dev-usb-session.lock
mkdir -p -- "$(dirname -- "$session_lock")" "$session_dir"
exec 8>"$session_lock"
flock -n 8 || { echo "start-nodehost-dev: another VM USB lifecycle operation is running" >&2; exit 1; }

state=$(virsh -c qemu:///system domstate nodehost-dev | tr -d '\r' | head -n 1)
case $state in
  running|shut\ off) ;;
  *) echo "start-nodehost-dev: refusing VM state $state" >&2; exit 1 ;;
esac

vm_started_by_us=false
session_active=false
monitor_started=false

cleanup_failed_start() {
  local status=$?
  trap - EXIT
  rm -f -- "$session_dir/nodehost-dev-usb.starting"
  if [[ $vm_started_by_us == true ]]; then
    virsh -c qemu:///system shutdown nodehost-dev >/dev/null 2>&1 || true
    for ((elapsed = 0; elapsed < 60; elapsed++)); do
      state=$(virsh -c qemu:///system domstate nodehost-dev 2>/dev/null | tr -d '\r' | head -n 1 || true)
      [[ $state == 'shut off' ]] && break
      sleep 1
    done
  fi
  if [[ $vm_started_by_us == false || $state == 'shut off' ]]; then
    if [[ $monitor_started == true ]]; then
      systemctl stop "$monitor_service" >/dev/null 2>&1 || true
    fi
    if [[ $session_active == true ]]; then
      "$reconciler" --cleanup-session --config "$config_file" >/dev/null 2>&1 || true
    fi
  else
    echo "start-nodehost-dev: graceful cleanup timed out; VM remains running and USB session remains active" >&2
  fi
  exit "$status"
}
trap cleanup_failed_start EXIT

"$reconciler" --activate-session --config "$config_file"
session_active=true
"$reconciler" --detach-persistent --config "$config_file"
"$reconciler" --preflight --config "$config_file"

if [[ $state != running ]]; then
  virsh -c qemu:///system start nodehost-dev >/dev/null
  vm_started_by_us=true
fi

"$reconciler" --apply --config "$config_file"
state=$(virsh -c qemu:///system domstate nodehost-dev | tr -d '\r' | head -n 1)
[[ $state == running ]] || { echo "start-nodehost-dev: refusing to start event monitor while VM is $state" >&2; exit 1; }

# Mark the monitor for cleanup before asking systemd to start it.  If the
# start request fails after creating a unit, the failure trap still stops it.
monitor_started=true
systemctl start "$monitor_service"
systemctl is-active --quiet "$monitor_service" || { echo "start-nodehost-dev: event monitor did not remain active" >&2; exit 1; }

rm -f -- "$session_dir/nodehost-dev-usb.starting"
trap - EXIT
echo "nodehost-dev is running with the exact USB HIL session active"
