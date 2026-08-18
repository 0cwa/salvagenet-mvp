#!/usr/bin/env bash
set -euo pipefail

# Explicit installer. Nothing is installed unless --apply is supplied.
# The historical 30-second timer is deliberately not part of the installed
# path. USB activation is owned by the explicit start wrapper and udev events.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
reconciler=$script_dir/reconcile-usb-device.sh
xml_helper=$script_dir/usb-hostdev-xml.py
start_wrapper=$script_dir/start-nodehost-dev-with-usb.sh
stop_wrapper=$script_dir/stop-nodehost-dev-with-usb.sh
monitor=$script_dir/usb-session-monitor.py
udev_template=$script_dir/udev/99-salvagehost-usb.rules.in
service_template=$script_dir/systemd/salvagehost-usb-reconcile.service
timer_template=$script_dir/systemd/salvagehost-usb-reconcile.timer
config_file=$script_dir/usb-device.conf
operation=

install_root=/usr/local/libexec/salvagehost
install_reconciler=$install_root/reconcile-usb-device.sh
install_xml_helper=$install_root/usb-hostdev-xml.py
install_start_wrapper=$install_root/start-nodehost-dev-with-usb.sh
install_stop_wrapper=$install_root/stop-nodehost-dev-with-usb.sh
install_monitor=$install_root/usb-session-monitor.py
install_config=/etc/salvagehost/nodehost-dev-usb.conf
legacy_udev=/etc/udev/rules.d/99-salvagehost-nodehost-dev-usb.rules
install_service=/etc/systemd/system/salvagehost-usb-reconcile.service
install_timer=/etc/systemd/system/salvagehost-usb-reconcile.timer
installer_state=/var/lib/salvagehost/usb/installer/nodehost-dev

usage() {
  cat >&2 <<'EOF'
usage: install-usb-reconciler.sh --check [--config FILE]
       install-usb-reconciler.sh --dry-run [--config FILE]
       install-usb-reconciler.sh --apply [--config FILE]
       install-usb-reconciler.sh --status
       install-usb-reconciler.sh --rollback

--check       validate source files, dependencies, and the non-secret config.
--dry-run     print managed paths and the rendered udev rule; no writes.
--apply       install wrappers, monitor, and event service; remove any old
              persistent udev rule; disable and remove the historical periodic
              timer; never starts the VM, USB reconciliation, or ADB.
--status      inspect installed paths and legacy timer state without changing.
--rollback    restore the most recent pre-apply files and leave the timer
              disabled.

The legacy timer source remains in the repository as a manual reference only;
the installer never installs or enables it.
EOF
}

die() {
  echo "install-usb-reconciler: $*" >&2
  exit 1
}

while (($#)); do
  case $1 in
    --config)
      (($# >= 2)) || { usage; exit 2; }
      config_file=$2
      shift 2
      ;;
    --check|--dry-run|--apply|--status|--rollback)
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
if [[ $operation != status && $operation != rollback ]]; then
  [[ -f $config_file ]] || die "missing config $config_file"
fi

for required in "$reconciler" "$xml_helper" "$start_wrapper" "$stop_wrapper" "$monitor" "$udev_template" "$service_template" "$timer_template"; do
  [[ -f $required ]] || die "missing source file $required"
done

config_value() {
  local wanted=$1
  awk -F= -v wanted="$wanted" '
    $0 !~ /^[[:space:]]*#/ && $0 ~ /^[A-Z][A-Z0-9_]*=/ && $1 == wanted { print substr($0, index($0, "=") + 1); found++ }
    END { if (found != 1) exit 1 }
  ' "$config_file"
}

validate_config() {
  [[ -f $config_file && -r $config_file ]] || die "missing or unreadable config $config_file"
  "$reconciler" --validate-config --config "$config_file" >/dev/null
  vm_name=$(config_value SALVAGEHOST_USB_VM_NAME)
  serial=$(config_value SALVAGEHOST_USB_SERIAL)
  vendor=$(config_value SALVAGEHOST_USB_VENDOR_ID | tr '[:upper:]' '[:lower:]')
  product=$(config_value SALVAGEHOST_USB_PRODUCT_ID | tr '[:upper:]' '[:lower:]')
  port=$(config_value SALVAGEHOST_USB_PHYSICAL_PORT)
  qemu_group=$(awk -F= '$0 !~ /^[[:space:]]*#/ && $1 == "SALVAGEHOST_USB_QEMU_GROUP" { print substr($0, index($0, "=") + 1); found++ } END { if (found > 1) exit 1 }' "$config_file")
  qemu_group=${qemu_group:-qemu}
  [[ $vm_name == nodehost-dev ]] || die "config must target nodehost-dev"
  [[ $vendor == 18d1 && $product == 4ee7 ]] || die "config must target 18d1:4ee7"
  [[ $serial == 5VT7N16607000293 ]] || die "config must target the authorized HIL phone"
  [[ $port == 3-2 ]] || die "config must target physical port 3-2"
  getent group "$qemu_group" >/dev/null || die "configured qemu group does not exist: $qemu_group"
  [[ $config_file != */.env && $config_file != */.env.* ]] || die "credential-bearing .env is not a USB config"
  ! grep -Eq '^(GITHUB_TOKEN|OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY|SSH_PRIVATE_KEY)=' "$config_file" || die "credential-like key found in USB config"
}

render_udev() {
  local output=$1
  sed \
    -e "s/@USB_VENDOR_ID@/$vendor/g" \
    -e "s/@USB_PRODUCT_ID@/$product/g" \
    -e "s/@USB_SERIAL@/$serial/g" \
    -e "s/@USB_PHYSICAL_PORT@/$port/g" \
    -e "s/@QEMU_GROUP@/$qemu_group/g" \
    "$udev_template" > "$output"
  ! grep -q '@[A-Z_][A-Z_]*@' "$output" || die "udev template was not fully rendered"
}

show_plan() {
  local rendered=$1
  echo "managed target: $install_reconciler"
  echo "managed target: $install_xml_helper"
  echo "managed target: $install_start_wrapper"
  echo "managed target: $install_stop_wrapper"
  echo "managed target: $install_monitor"
  echo "managed target: $install_config"
  echo "managed target: $install_service"
  echo "legacy persistent udev rule removed if present: $legacy_udev"
  echo "legacy timer source: $timer_template (not installed or enabled)"
  echo "configured identity: serial=$serial vidpid=${vendor}:${product} physical-port=$port"
  echo "runtime-only udev rule: /run/udev/rules.d/99-salvagehost-nodehost-dev-usb.rules"
  echo "udev rule (rendered for the active session; never installed under /etc):"
  sed -n '1,8p' "$rendered"
  echo "persistent libvirt USB hostdev: absent; live bus/device attachment is temporary"
  echo "activation: explicit root start wrapper plus monitor-observed USB add/change events"
  echo "ADB action: none; competing adb/adbd causes refusal"
}

disable_legacy_timer() {
  systemctl disable --now salvagehost-usb-reconcile.timer >/dev/null 2>&1 || true
  if systemctl is-enabled --quiet salvagehost-usb-reconcile.timer 2>/dev/null; then
    die "legacy USB timer remains enabled; refusing to continue"
  fi
  if systemctl is-active --quiet salvagehost-usb-reconcile.timer 2>/dev/null; then
    die "legacy USB timer remains active; refusing to continue"
  fi
}

check_dependencies() {
  for command in awk bash basename cat cp date dirname flock getent grep head install mkdir mktemp mv \
                 printf pwd python3 rm rmdir sed sha256sum sleep stat systemctl tr udevadm virsh; do
    command -v "$command" >/dev/null || die "missing required command $command"
  done
}

if [[ $operation == status ]]; then
  printf 'installer state: %s\n' "$installer_state"
  for target in "$install_reconciler" "$install_xml_helper" "$install_start_wrapper" "$install_stop_wrapper" "$install_monitor" "$install_config" "$install_service"; do
    if [[ -e $target ]]; then
      printf 'installed: %s sha256=%s\n' "$target" "$(sha256sum "$target" | awk '{print $1}')"
    else
      printf 'missing: %s\n' "$target"
    fi
  done
  if [[ -e $legacy_udev ]]; then echo "legacy persistent udev rule: present (must be removed)"; else echo "legacy persistent udev rule: absent"; fi
  if systemctl is-enabled --quiet salvagehost-usb-reconcile.timer 2>/dev/null; then echo 'legacy timer: enabled (installer must disable)'; else echo 'legacy timer: disabled-or-absent'; fi
  if systemctl is-active --quiet salvagehost-usb-reconcile.timer 2>/dev/null; then echo 'legacy timer: active (installer must stop)'; else echo 'legacy timer: inactive-or-absent'; fi
  exit 0
fi

if [[ $operation == rollback ]]; then
  [[ $EUID -eq 0 ]] || die "--rollback requires root"
  [[ -f $installer_state/manifest ]] || die "no rollback manifest at $installer_state/manifest"
  if systemctl is-active --quiet salvagehost-usb-reconcile.service 2>/dev/null; then
    die "reconciliation service is active; wait for it to finish before rollback"
  fi
  disable_legacy_timer
  while IFS='|' read -r state target backup; do
    [[ -n $target ]] || continue
    if [[ $state == existing ]]; then
      install -D -m 0644 "$backup" "$target"
    elif [[ $state == absent ]]; then
      rm -f -- "$target"
    else
      die "invalid rollback manifest entry"
    fi
  done < "$installer_state/manifest"
  systemctl daemon-reload
  disable_legacy_timer
  udevadm control --reload-rules
  echo "rollback complete; legacy timer disabled; backup retained under $installer_state"
  exit 0
fi

check_dependencies
validate_config
render_dir=$(mktemp -d)
trap 'rm -rf -- "$render_dir"' EXIT
rendered_udev=$render_dir/99-salvagehost-nodehost-dev-usb.rules
render_udev "$rendered_udev"

case $operation in
  check)
    echo "source and config validation passed"
    show_plan "$rendered_udev"
    ;;
  dry-run)
    show_plan "$rendered_udev"
    echo "dry-run complete; no files, udev rules, systemd units, timer, VM, USB, or ADB state changed"
    ;;
  apply)
    [[ $EUID -eq 0 ]] || die "--apply requires root"
    mkdir -p -- "$installer_state"
    backup_dir=$installer_state/backup-$(date +%Y%m%dT%H%M%S)-$$
    mkdir -p -- "$backup_dir"
    : > "$installer_state/manifest"
    record_target() {
      local target=$1 backup
      if [[ -e $target ]]; then
        backup=$backup_dir${target}
        mkdir -p -- "$(dirname -- "$backup")"
        cp -a -- "$target" "$backup"
        printf 'existing|%s|%s\n' "$target" "$backup" >> "$installer_state/manifest"
      else
        printf 'absent|%s|\n' "$target" >> "$installer_state/manifest"
      fi
    }
    for target in "$install_reconciler" "$install_xml_helper" "$install_start_wrapper" "$install_stop_wrapper" "$install_monitor" "$install_config" "$legacy_udev" "$install_service" "$install_timer"; do
      record_target "$target"
    done
    # Quiesce and verify the legacy timer before touching managed files. The
    # persistent udev rule is deliberately removed, never replaced.
    disable_legacy_timer
    install -d -m 0755 "$install_root" /etc/salvagehost /etc/systemd/system
    install -m 0755 "$reconciler" "$install_reconciler"
    install -m 0755 "$xml_helper" "$install_xml_helper"
    install -m 0755 "$start_wrapper" "$install_start_wrapper"
    install -m 0755 "$stop_wrapper" "$install_stop_wrapper"
    install -m 0755 "$monitor" "$install_monitor"
    install -m 0644 "$config_file" "$install_config"
    install -m 0644 "$service_template" "$install_service"
    rm -f -- "$legacy_udev"
    rm -f -- "$install_timer"
    systemctl daemon-reload
    disable_legacy_timer
    udevadm control --reload-rules
    echo "apply complete; rollback manifest: $installer_state/manifest"
    echo "legacy timer disabled/removed; use the explicit start wrapper and USB events"
    ;;
  *)
    usage
    exit 2
    ;;
esac
