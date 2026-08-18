#!/usr/bin/env bash
set -euo pipefail

# Strict start-scoped USB lifecycle for the one physical HIL phone.
#
# Persistent libvirt XML is deliberately not used for this device.  The
# start wrapper removes any old matching persistent hostdev, then this script
# attaches the current USB bus/device address with --live only.  Runtime udev
# access exists only while the /run session marker and rule exist.  This file
# never invokes adb or changes ADB ownership.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
xml_helper=$script_dir/usb-hostdev-xml.py
config_file=/etc/salvagehost/nodehost-dev-usb.conf
operation=

usage() {
  cat >&2 <<'EOF'
usage: reconcile-usb-device.sh --validate-config [--config FILE]
       reconcile-usb-device.sh --dry-run [--config FILE]
       reconcile-usb-device.sh --check [--config FILE]
       reconcile-usb-device.sh --status [--config FILE]
       reconcile-usb-device.sh --activate-session [--config FILE]
       reconcile-usb-device.sh --cleanup-session [--config FILE]
       reconcile-usb-device.sh --detach-persistent [--config FILE]
       reconcile-usb-device.sh --preflight [--config FILE]
       reconcile-usb-device.sh --apply [--config FILE]
       reconcile-usb-device.sh --event [--config FILE]

--activate-session    install the transient /run udev rule and marker.
--cleanup-session     remove the marker/rule and restore ordinary udev access.
--detach-persistent   remove only the exact configured hostdev from inactive
                      libvirt XML; it never attaches a persistent hostdev.
--preflight           verify the exact phone, qemu access, ADB boundary, VM
                      state, and absence of a persistent matching hostdev.
--apply               attach or repair the exact current USB address live.
--event               the same live repair used by the event monitor; it is
                      mutating and requires an active session.
EOF
}

die() {
  echo "reconcile-usb-device: $*" >&2
  exit 1
}

invalid_config() {
  echo "reconcile-usb-device: invalid config: $*" >&2
  exit 2
}

while (($#)); do
  case $1 in
    --config)
      (($# >= 2)) || { usage; exit 2; }
      config_file=$2
      shift 2
      ;;
    --validate-config|--dry-run|--check|--status|--activate-session|--cleanup-session|--detach-persistent|--preflight|--apply|--event)
      [[ -z $operation ]] || { usage; exit 2; }
      operation=${1#--}
      shift
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

[[ -n $operation ]] || { usage; exit 2; }
[[ -f $config_file ]] || invalid_config "missing $config_file"
[[ -r $config_file ]] || invalid_config "cannot read $config_file"
[[ $(basename -- "$config_file") != .env && $(basename -- "$config_file") != .env.* ]] || invalid_config "credential-bearing .env files are not valid USB config"
if grep -Eq '^(GITHUB_TOKEN|OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY|SSH_PRIVATE_KEY)=' "$config_file"; then
  invalid_config "credential-like keys are not allowed"
fi

declare -A seen_keys=()
allowed_key() {
  case $1 in
    SALVAGEHOST_USB_VM_NAME|SALVAGEHOST_USB_SERIAL|SALVAGEHOST_USB_VENDOR_ID|SALVAGEHOST_USB_PRODUCT_ID|SALVAGEHOST_USB_PHYSICAL_PORT|SALVAGEHOST_USB_MODE|SALVAGEHOST_USB_QEMU_GROUP|SALVAGEHOST_USB_LIBVIRT_URI|SALVAGEHOST_USB_LOCK_FILE|SALVAGEHOST_USB_STATE_DIR|SALVAGEHOST_USB_STOP_TIMEOUT_SEC)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

while IFS= read -r line || [[ -n $line ]]; do
  [[ -z $line || $line == \#* ]] && continue
  [[ $line =~ ^([A-Z][A-Z0-9_]*)=(.*)$ ]] || invalid_config "expected KEY=VALUE"
  key=${BASH_REMATCH[1]}
  value=${BASH_REMATCH[2]}
  allowed_key "$key" || invalid_config "unknown key $key"
  [[ -z ${seen_keys[$key]+x} ]] || invalid_config "duplicate key $key"
  [[ $value != *$'\n'* && $value != *$'\r'* ]] || invalid_config "newline in $key"
  seen_keys[$key]=1
  printf -v "$key" '%s' "$value"
done < "$config_file"

: "${SALVAGEHOST_USB_VM_NAME:?SALVAGEHOST_USB_VM_NAME is required}"
: "${SALVAGEHOST_USB_SERIAL:?SALVAGEHOST_USB_SERIAL is required}"
: "${SALVAGEHOST_USB_VENDOR_ID:?SALVAGEHOST_USB_VENDOR_ID is required}"
: "${SALVAGEHOST_USB_PRODUCT_ID:?SALVAGEHOST_USB_PRODUCT_ID is required}"
: "${SALVAGEHOST_USB_PHYSICAL_PORT:?SALVAGEHOST_USB_PHYSICAL_PORT is required}"
: "${SALVAGEHOST_USB_MODE:?SALVAGEHOST_USB_MODE is required}"
: "${SALVAGEHOST_USB_LIBVIRT_URI:?SALVAGEHOST_USB_LIBVIRT_URI is required}"
: "${SALVAGEHOST_USB_LOCK_FILE:?SALVAGEHOST_USB_LOCK_FILE is required}"
: "${SALVAGEHOST_USB_STATE_DIR:?SALVAGEHOST_USB_STATE_DIR is required}"
: "${SALVAGEHOST_USB_STOP_TIMEOUT_SEC:?SALVAGEHOST_USB_STOP_TIMEOUT_SEC is required}"

[[ $SALVAGEHOST_USB_VM_NAME =~ ^[A-Za-z0-9._-]+$ ]] || invalid_config "invalid VM name"
[[ $SALVAGEHOST_USB_VM_NAME == nodehost-dev ]] || invalid_config "only nodehost-dev is supported"
[[ $SALVAGEHOST_USB_SERIAL == 5VT7N16607000293 ]] || invalid_config "configured USB serial is not the authorized HIL phone"
[[ ${SALVAGEHOST_USB_VENDOR_ID,,} == 18d1 && ${SALVAGEHOST_USB_PRODUCT_ID,,} == 4ee7 ]] || invalid_config "configured VID/PID is not the authorized HIL phone"
[[ $SALVAGEHOST_USB_PHYSICAL_PORT == 3-2 ]] || invalid_config "configured physical port is not the authorized HIL port"
[[ $SALVAGEHOST_USB_SERIAL =~ ^[A-Za-z0-9._:-]+$ ]] || invalid_config "invalid USB serial"
for id in "$SALVAGEHOST_USB_VENDOR_ID" "$SALVAGEHOST_USB_PRODUCT_ID"; do
  [[ $id =~ ^[[:xdigit:]]{4}$ ]] || invalid_config "USB IDs must be four hexadecimal digits"
done
[[ $SALVAGEHOST_USB_PHYSICAL_PORT =~ ^[0-9]+(-[0-9]+)+(\.[0-9]+)*$ ]] || invalid_config "invalid physical USB port"
[[ $SALVAGEHOST_USB_MODE == guest-usb ]] || invalid_config "only guest-usb mode is supported by this reconciler"
SALVAGEHOST_USB_QEMU_GROUP=${SALVAGEHOST_USB_QEMU_GROUP:-qemu}
[[ $SALVAGEHOST_USB_QEMU_GROUP =~ ^[a-z_][a-z0-9_-]*$ ]] || invalid_config "invalid qemu group"
[[ $SALVAGEHOST_USB_LIBVIRT_URI == qemu:///system ]] || invalid_config "only qemu:///system is supported"
[[ $SALVAGEHOST_USB_LOCK_FILE == /* ]] || invalid_config "lock file must be absolute"
[[ $SALVAGEHOST_USB_STATE_DIR == /* ]] || invalid_config "state directory must be absolute"
[[ $SALVAGEHOST_USB_STOP_TIMEOUT_SEC =~ ^[1-9][0-9]*$ ]] || invalid_config "stop timeout must be positive"
[[ -x $xml_helper ]] || invalid_config "missing executable $xml_helper"
command -v getent >/dev/null 2>&1 || invalid_config "getent is required to validate the qemu group"
getent group "$SALVAGEHOST_USB_QEMU_GROUP" >/dev/null || invalid_config "qemu group does not exist: $SALVAGEHOST_USB_QEMU_GROUP"

if [[ $operation == validate-config ]]; then
  echo "config valid: $config_file"
  echo "target: $SALVAGEHOST_USB_VM_NAME / serial $SALVAGEHOST_USB_SERIAL / ${SALVAGEHOST_USB_VENDOR_ID,,}:${SALVAGEHOST_USB_PRODUCT_ID,,} / port $SALVAGEHOST_USB_PHYSICAL_PORT"
  exit 0
fi

session_dir=/run/salvagehost
session_marker=$session_dir/nodehost-dev-usb.active
session_starting=$session_dir/nodehost-dev-usb.starting
runtime_rule_dir=/run/udev/rules.d
runtime_rule=$runtime_rule_dir/99-salvagehost-nodehost-dev-usb.rules
guest_address_file=$session_dir/nodehost-dev-usb.guest-address
sysfs_root=${SALVAGEHOST_USB_SYSFS_ROOT:-/sys/bus/usb/devices}
proc_root=${SALVAGEHOST_USB_PROC_ROOT:-/proc}
dev_root=${SALVAGEHOST_USB_DEV_ROOT:-/dev/bus/usb}

vendor=${SALVAGEHOST_USB_VENDOR_ID,,}
product=${SALVAGEHOST_USB_PRODUCT_ID,,}
uri=$SALVAGEHOST_USB_LIBVIRT_URI
vm=$SALVAGEHOST_USB_VM_NAME

require_command() {
  command -v "$1" >/dev/null || die "$1 is required"
}

require_root() {
  [[ $EUID -eq 0 ]] || die "--$operation requires root"
}

acquire_reconcile_lock() {
  local parent
  require_command flock
  parent=$(dirname -- "$SALVAGEHOST_USB_LOCK_FILE")
  [[ -d $parent ]] || mkdir -p -- "$parent"
  exec 9>"$SALVAGEHOST_USB_LOCK_FILE"
  flock -n 9 || die "another USB reconciliation is already running"
}

device_present=false
device_sysfs_path=
device_node=
device_bus=
device_number=

find_device() {
  local path serial id_vendor id_product port bus device candidate_count=0 wrong_port=
  device_sysfs_path=
  device_node=
  device_bus=
  device_number=
  shopt -s nullglob
  for path in "$sysfs_root"/*; do
    [[ -f $path/idVendor && -f $path/idProduct && -f $path/serial ]] || continue
    id_vendor=$(<"$path/idVendor")
    id_product=$(<"$path/idProduct")
    serial=$(<"$path/serial")
    [[ ${id_vendor,,} == "$vendor" && ${id_product,,} == "$product" && $serial == "$SALVAGEHOST_USB_SERIAL" ]] || continue
    port=${path##*/}
    if [[ $port != "$SALVAGEHOST_USB_PHYSICAL_PORT" ]]; then
      wrong_port=$port
      continue
    fi
    [[ -f $path/busnum && -f $path/devnum ]] || die "USB identity has no bus/device metadata"
    bus=$(<"$path/busnum")
    device=$(<"$path/devnum")
    [[ $bus =~ ^[0-9]+$ && $device =~ ^[0-9]+$ ]] || die "USB bus/device metadata is invalid"
    candidate_count=$((candidate_count + 1))
    device_sysfs_path=$path
    device_bus=$bus
    device_number=$device
    printf -v device_node '%s/%03d/%03d' "$dev_root" "$bus" "$device"
  done
  shopt -u nullglob
  [[ -z $wrong_port ]] || die "exact USB identity found on unexpected physical port $wrong_port"
  ((candidate_count <= 1)) || die "exact USB identity is ambiguous ($candidate_count matches)"
  if ((candidate_count == 0)); then
    device_present=false
    return 0
  fi
  device_present=true
}

refuse_competing_adb() {
  local proc comm owner
  for proc in "$proc_root"/[0-9]*; do
    [[ -r $proc/comm ]] || continue
    comm=$(<"$proc/comm")
    [[ $comm == adb || $comm == adbd ]] || continue
    owner=$(stat -c '%U' "$proc" 2>/dev/null || echo unknown)
    echo "competing ADB process detected (owner $owner); refusing USB ownership change" >&2
    return 3
  done
  return 0
}

check_qemu_access() {
  [[ -e $device_node ]] || die "USB device node is absent: $device_node"
  local group mode
  group=$(stat -c '%G' "$device_node") || die "cannot inspect $device_node"
  mode=$(stat -c '%a' "$device_node") || die "cannot inspect $device_node"
  [[ $group == "$SALVAGEHOST_USB_QEMU_GROUP" ]] || die "USB node group is $group, expected $SALVAGEHOST_USB_QEMU_GROUP"
  [[ $mode =~ ^[0-9]{3,4}$ ]] || die "USB node mode is invalid: $mode"
  local group_bits=${mode: -2:1}
  [[ $group_bits == 6 || $group_bits == 7 ]] || die "USB node group is not readable/writable (mode $mode)"
}

domain_state() {
  virsh -c "$uri" domstate "$vm" | tr -d '\r' | head -n 1
}

write_runtime_rule() {
  mkdir -p -- "$session_dir" "$runtime_rule_dir"
  local temp_rule=$runtime_rule_dir/.99-salvagehost-nodehost-dev-usb.rules.$$
  umask 022
  cat > "$temp_rule" <<EOF
# Runtime-only rule. The marker is created after this file is present and is
# removed before the rule is deleted, so qemu access is never enabled by a
# half-created session.
ACTION=="add|change", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", KERNEL=="$SALVAGEHOST_USB_PHYSICAL_PORT", ATTR{idVendor}=="$vendor", ATTR{idProduct}=="$product", ATTR{serial}=="$SALVAGEHOST_USB_SERIAL", TEST=="$session_marker", GROUP="$SALVAGEHOST_USB_QEMU_GROUP", MODE="0660"
EOF
  mv -f -- "$temp_rule" "$runtime_rule"
}

trigger_exact_device() {
  require_command udevadm
  udevadm control --reload-rules
  udevadm trigger --action=change --subsystem-match=usb --sysname-match="$SALVAGEHOST_USB_PHYSICAL_PORT"
  udevadm settle --timeout=10
}

cleanup_session_unlocked() {
  # Remove the marker first while the rule still exists, then re-evaluate the
  # exact node under ordinary udev policy, and finally remove the rule.
  rm -f -- "$session_starting" "$session_marker"
  if command -v udevadm >/dev/null 2>&1; then
    udevadm control --reload-rules || true
    udevadm trigger --action=change --subsystem-match=usb --sysname-match="$SALVAGEHOST_USB_PHYSICAL_PORT" || true
    udevadm settle --timeout=10 || true
    udevadm control --reload-rules || true
  fi
  rm -f -- "$runtime_rule" "$guest_address_file"
}

activate_session() (
  require_root
  require_command udevadm
  udevadm settle --timeout=10
  refuse_competing_adb
  find_device
  [[ $device_present == true ]] || die "exact configured USB device is absent"
  write_runtime_rule
  : > "$session_marker"
  : > "$session_starting"
  activation_cleanup() {
    local status=$?
    trap - EXIT
    cleanup_session_unlocked || true
    exit "$status"
  }
  trap activation_cleanup EXIT
  trigger_exact_device || die "transient udev session activation failed"
  find_device
  check_qemu_access
  trap - EXIT
  echo "USB session active for serial $SALVAGEHOST_USB_SERIAL on physical port $SALVAGEHOST_USB_PHYSICAL_PORT"
)

dump_xml() {
  local mode=$1 output=$2
  if [[ $mode == live ]]; then
    virsh -c "$uri" dumpxml "$vm" > "$output" || die "cannot read live XML for $vm"
  else
    virsh -c "$uri" dumpxml --inactive "$vm" > "$output" || die "cannot read persistent XML for $vm"
  fi
}

persistent_is_absent() {
  local xml=$1
  python3 "$xml_helper" check-absent --xml "$xml" --vendor "$vendor" --product "$product" >/dev/null
}

detach_persistent() {
  require_root
  require_command virsh
  local xml=$tmp_dir/persistent.xml detach=$tmp_dir/persistent-detach.xml
  dump_xml inactive "$xml"
  if persistent_is_absent "$xml"; then
    echo "persistent XML: exact USB hostdev absent"
    return 0
  fi
  python3 "$xml_helper" extract --xml "$xml" --vendor "$vendor" --product "$product" > "$detach" || die "persistent USB hostdev is ambiguous or cannot be identified"
  virsh -c "$uri" detach-device "$vm" "$detach" --config || die "could not remove exact persistent USB hostdev"
  dump_xml inactive "$xml"
  persistent_is_absent "$xml" || die "persistent USB hostdev removal postcondition failed"
  echo "persistent XML: exact USB hostdev removed; future attachment is live-only"
}

read_guest_address() {
  guest_bus=
  guest_port=
  if [[ -r $guest_address_file ]]; then
    IFS=: read -r guest_bus guest_port < "$guest_address_file" || true
    [[ $guest_bus =~ ^[0-9]+$ && $guest_port =~ ^[0-9]+$ ]] || { guest_bus=; guest_port=; }
  fi
}

save_guest_address_from_live() {
  local live_xml=$1 address
  address=$(python3 "$xml_helper" guest-address-by-source --xml "$live_xml" --bus "$device_bus" --device "$device_number" 2>/dev/null || true)
  if [[ $address == *:* ]]; then
    printf '%s\n' "$address" > "$guest_address_file"
    IFS=: read -r guest_bus guest_port <<<"$address"
  fi
}

attach_live() {
  require_root
  require_command udevadm
  require_command virsh
  require_command python3
  [[ -e $session_marker ]] || die "live attachment requires an active USB session"
  [[ $(domain_state) == running ]] || die "live attachment requires nodehost-dev to be running"
  refuse_competing_adb
  udevadm settle --timeout=10
  find_device
  [[ $device_present == true ]] || die "exact configured USB device is absent"
  udevadm trigger --action=change "$device_sysfs_path"
  udevadm settle --timeout=10
  find_device
  check_qemu_access

  local live_xml=$tmp_dir/live.xml detach=$tmp_dir/live-detach.xml live_plan=$tmp_dir/live-plan.xml
  dump_xml live "$live_xml"
  read_guest_address
  local check_args=(--xml "$live_xml" --vendor "$vendor" --product "$product" --bus "$device_bus" --device "$device_number")
  [[ -n $guest_bus && -n $guest_port ]] && check_args+=(--guest-bus "$guest_bus" --guest-port "$guest_port")
  if python3 "$xml_helper" check-live "${check_args[@]}" >/dev/null 2>&1; then
    echo "live XML: exact hostdev already points at the current USB address"
    return 0
  fi

  local detach_args=(--xml "$live_xml" --vendor "$vendor" --product "$product")
  [[ -n $guest_bus && -n $guest_port ]] && detach_args+=(--guest-bus "$guest_bus" --guest-port "$guest_port")
  if python3 "$xml_helper" extract "${detach_args[@]}" > "$detach" 2>/dev/null; then
    echo "live XML: detaching only the exact stale configured hostdev"
    virsh -c "$uri" detach-device "$vm" "$detach" --live || die "stale live hostdev detach failed"
  elif grep -q '<hostdev ' "$live_xml"; then
    die "live USB state is stale but the exact hostdev cannot be identified safely"
  fi

  cat > "$live_plan" <<EOF
<hostdev mode='subsystem' type='usb' managed='yes'>
  <source><address bus='$device_bus' device='$device_number'/></source>
$(if [[ -n $guest_bus && -n $guest_port ]]; then echo "  <address type='usb' bus='$guest_bus' port='$guest_port'/>"; fi)
</hostdev>
EOF
  echo "live XML: attaching current bus/device address ephemerally"
  virsh -c "$uri" attach-device "$vm" "$live_plan" --live || die "live hostdev attach failed"
  dump_xml live "$live_xml"
  save_guest_address_from_live "$live_xml"
  read_guest_address
  if [[ -n $guest_bus && -n $guest_port ]]; then
    python3 "$xml_helper" check-live --xml "$live_xml" --vendor "$vendor" --product "$product" --bus "$device_bus" --device "$device_number" --guest-bus "$guest_bus" --guest-port "$guest_port" >/dev/null || die "live hostdev postcondition failed"
  else
    python3 "$xml_helper" check-source-address --xml "$live_xml" --bus "$device_bus" --device "$device_number" >/dev/null || die "live USB source postcondition failed"
  fi
  echo "live XML: current exact USB attachment verified"
}

write_status() {
  local state=$1
  mkdir -p -- "$SALVAGEHOST_USB_STATE_DIR"
  local status_tmp=$SALVAGEHOST_USB_STATE_DIR/.status.tmp
  umask 077
  cat > "$status_tmp" <<EOF
timestamp=$(date --iso-8601=seconds)
vm_name=$SALVAGEHOST_USB_VM_NAME
serial=$SALVAGEHOST_USB_SERIAL
vendor_id=$vendor
product_id=$product
physical_port=$SALVAGEHOST_USB_PHYSICAL_PORT
live_state=$state
persistent_hostdev=absent
EOF
  mv -f -- "$status_tmp" "$SALVAGEHOST_USB_STATE_DIR/status"
}

preflight() {
  require_root
  require_command udevadm
  require_command virsh
  [[ -e $session_marker ]] || die "--preflight requires an active USB session"
  udevadm settle --timeout=10
  refuse_competing_adb
  find_device
  [[ $device_present == true ]] || die "exact configured USB device is absent"
  check_qemu_access
  local state
  state=$(domain_state)
  [[ $state == running || $state == 'shut off' ]] || die "refusing VM state $state"
  dump_xml inactive "$tmp_dir/persistent.xml"
  persistent_is_absent "$tmp_dir/persistent.xml" || die "persistent XML still contains the physical USB hostdev"
  echo "preflight passed: exact device, qemu access, no competing ADB, VM state=$state, persistent hostdev absent"
}

check_read_only() {
  require_command udevadm
  udevadm settle --timeout=10
  refuse_competing_adb
  find_device
  if [[ $device_present == true ]]; then
    echo "device: present at serial $SALVAGEHOST_USB_SERIAL on physical port $SALVAGEHOST_USB_PHYSICAL_PORT"
    echo "device node: $device_node"
  else
    echo "device: absent"
  fi
  if command -v virsh >/dev/null 2>&1; then
    dump_xml inactive "$tmp_dir/persistent.xml"
    if persistent_is_absent "$tmp_dir/persistent.xml"; then
      echo "persistent XML: exact USB hostdev absent"
    else
      echo "persistent XML: exact USB hostdev present and must be removed by the start wrapper"
    fi
  fi
}

dry_run() {
  cat <<EOF
strict start-scoped USB plan:
  target: $vm serial=$SALVAGEHOST_USB_SERIAL vidpid=$vendor:$product physical-port=$SALVAGEHOST_USB_PHYSICAL_PORT
  install: transient /run/udev rule only while the session marker exists
  start: remove exact persistent hostdev, start VM, attach current USB address with --live
  recovery: event monitor invokes --event live repair on exact add/change events
  stop: graceful VM shutdown, then remove marker/rule and re-evaluate exact node
  timer: not installed, not enabled, not part of the normal path
  adb: never started, stopped, or authorized by this tooling
EOF
}

if [[ $operation == dry-run ]]; then
  dry_run
  exit 0
fi

if [[ $operation == status ]]; then
  status_file=$SALVAGEHOST_USB_STATE_DIR/status
  if [[ -r $status_file ]]; then
    cat -- "$status_file"
  else
    echo "status: unavailable (no persisted status at $status_file)"
  fi
  exit 0
fi

if [[ $operation == check ]]; then
  require_command flock
  tmp_dir=$(mktemp -d)
  trap 'rm -rf -- "$tmp_dir"' EXIT
  check_read_only
  exit 0
fi

require_root
require_command flock
require_command python3
tmp_dir=$(mktemp -d)
trap 'rm -rf -- "$tmp_dir"' EXIT

case $operation in
  activate-session|cleanup-session|detach-persistent|preflight|apply|event)
    acquire_reconcile_lock
    ;;
esac

case $operation in
  activate-session)
    activate_session
    ;;
  cleanup-session)
    cleanup_session_unlocked
    echo "USB session inactive; ordinary udev policy restored"
    ;;
  detach-persistent)
    require_command virsh
    detach_persistent
    ;;
  preflight)
    preflight
    ;;
  apply)
    attach_live
    write_status current
    ;;
  event)
    require_command virsh
    if [[ ! -e $session_marker ]]; then
      echo "USB event ignored: nodehost-dev session is inactive"
      exit 0
    fi
    if [[ $(domain_state) != running ]]; then
      cleanup_session_unlocked
      echo "USB event observed with a stopped VM; stale session cleaned"
      exit 0
    fi
    attach_live
    write_status current
    ;;
  *)
    usage
    exit 2
    ;;
esac
