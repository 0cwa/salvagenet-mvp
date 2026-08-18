#!/usr/bin/env bash
set -euo pipefail

# Repository-only validation. This script never invokes virsh, systemctl
# enable/start/stop, adb, udevadm trigger, or any VM/USB operation.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../.." && pwd -P)
cd -- "$repo_root"
tmp_dir=$(mktemp -d)
trap 'rm -rf -- "$tmp_dir"' EXIT

fail() {
  echo "validate-usb-reconciler: $*" >&2
  exit 1
}

for script in \
  "$script_dir/configure-usb-device.sh" \
  "$script_dir/reconcile-usb-device.sh" \
  "$script_dir/install-usb-reconciler.sh" \
  "$script_dir/start-nodehost-dev-with-usb.sh" \
  "$script_dir/stop-nodehost-dev-with-usb.sh"; do
  bash -n "$script" || fail "shell syntax failed: $script"
done

for python_file in "$script_dir/usb-hostdev-xml.py" "$script_dir/usb-session-monitor.py"; do
  python3 -c 'from pathlib import Path; import sys; path = Path(sys.argv[1]); compile(path.read_text(), str(path), "exec")' \
    "$python_file" || fail "Python syntax failed: $python_file"
done

"$script_dir/reconcile-usb-device.sh" --validate-config \
  --config "$script_dir/usb-device.conf.example" >/dev/null || fail "example config rejected"

if grep -Eq '^(GITHUB_TOKEN|OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY|SSH_PRIVATE_KEY)=' \
  "$script_dir/usb-device.conf.example"; then
  fail "example USB config contains credential-like keys"
fi

if grep -Eq 'RUN\{|RUN\+=' "$script_dir/udev/99-salvagehost-usb.rules.in"; then
  fail "udev rule performs work instead of only triggering systemd"
fi
grep -q 'GROUP="@QEMU_GROUP@"' "$script_dir/udev/99-salvagehost-usb.rules.in" || fail "udev qemu group access missing"
grep -q 'KERNEL=="@USB_PHYSICAL_PORT@"' "$script_dir/udev/99-salvagehost-usb.rules.in" || fail "udev physical-port match missing"
grep -q 'TEST=="/run/salvagehost/nodehost-dev-usb.active"' "$script_dir/udev/99-salvagehost-usb.rules.in" || fail "udev session gate missing"
if grep -q 'SYSTEMD_WANTS' "$script_dir/udev/99-salvagehost-usb.rules.in"; then
  fail "strict udev rule must not use SYSTEMD_WANTS"
fi
grep -q 'str(reconciler), "--event"' "$script_dir/usb-session-monitor.py" || fail "event monitor does not invoke --event"

cat > "$tmp_dir/persistent.xml" <<'EOF'
<domain><devices><disk type='file' device='disk'/></devices></domain>
EOF
python3 "$script_dir/usb-hostdev-xml.py" check-absent \
  --xml "$tmp_dir/persistent.xml" --vendor 18d1 --product 4ee7 >/dev/null || fail "persistent USB hostdev absence check failed"

if python3 "$script_dir/usb-hostdev-xml.py" check-persistent \
  --xml "$tmp_dir/persistent.xml" --vendor 18d1 --product 4ee7 \
  --startup-policy optional --guest-reset off >/dev/null 2>&1; then
  fail "persistent hostdev check accepted an absent hostdev"
fi

cat > "$tmp_dir/live.xml" <<'EOF'
<domain><devices>
  <hostdev mode='subsystem' type='usb' managed='yes'>
    <source><address bus='3' device='14'/></source>
    <address type='usb' bus='0' port='4'/>
  </hostdev>
</devices></domain>
EOF

python3 "$script_dir/usb-hostdev-xml.py" check-live \
  --xml "$tmp_dir/live.xml" --vendor 18d1 --product 4ee7 \
  --bus 3 --device 14 --guest-bus 0 --guest-port 4 >/dev/null || fail "live XML check failed"

if python3 "$script_dir/usb-hostdev-xml.py" check-live \
  --xml "$tmp_dir/live.xml" --vendor 18d1 --product 4ee7 \
  --bus 3 --device 15 --guest-bus 0 --guest-port 4 >/dev/null 2>&1; then
  fail "stale live bus/device address was accepted"
fi

installer_output=$("$script_dir/install-usb-reconciler.sh" --dry-run \
  --config "$script_dir/usb-device.conf.example") || fail "installer dry-run failed"
grep -q 'serial=5VT7N16607000293' <<<"$installer_output" || fail "exact serial missing from dry-run"
grep -q '18d1:4ee7' <<<"$installer_output" || fail "exact VID/PID missing from dry-run"
grep -q 'GROUP="qemu"' <<<"$installer_output" || fail "rendered qemu access missing from dry-run"
grep -q 'physical-port=3-2' <<<"$installer_output" || fail "physical port missing from dry-run"
grep -q 'runtime-only udev rule: /run/udev/rules.d/' <<<"$installer_output" || fail "transient /run udev path missing from dry-run"
grep -q 'never installed under /etc' <<<"$installer_output" || fail "dry-run does not prove udev rule is transient"
if grep -q 'SYSTEMD_WANTS' <<<"$installer_output"; then
  fail "dry-run still advertises SYSTEMD_WANTS"
fi
grep -q 'legacy timer source: .*not installed or enabled' <<<"$installer_output" || fail "dry-run does not prove timer is manual-only"
grep -q 'managed target: .*usb-session-monitor.py' <<<"$installer_output" || fail "dry-run omits the event monitor"

if grep -Eq 'systemctl (enable|start) salvagehost-usb-reconcile\.timer' \
  "$script_dir/install-usb-reconciler.sh"; then
  fail "installer still enables or starts the periodic timer"
fi
if grep -Eq 'install .*rendered_udev.*install_udev|install -m [0-9]+ .*rendered_udev.*udev/rules\.d' \
  "$script_dir/install-usb-reconciler.sh"; then
  fail "installer still installs a persistent udev rule"
fi
grep -q 'install -m 0755 "\$monitor" "\$install_monitor"' \
  "$script_dir/install-usb-reconciler.sh" || fail "installer omits the event monitor"
grep -q 'rm -f -- "\$legacy_udev"' "$script_dir/install-usb-reconciler.sh" || fail "installer does not remove the old persistent udev rule"
grep -q 'remains enabled; refusing to continue' "$script_dir/install-usb-reconciler.sh" || fail "installer does not fail closed on enabled timer"
grep -q 'remains active; refusing to continue' "$script_dir/install-usb-reconciler.sh" || fail "installer does not fail closed on active timer"
if "$script_dir/install-usb-reconciler.sh" --help 2>&1 | grep -Eq -- '--enable-timer|--start-timer'; then
  fail "installer still exposes timer activation flags"
fi

nonroot_output=$tmp_dir/nonroot.out
if "$script_dir/start-nodehost-dev-with-usb.sh" --config "$script_dir/usb-device.conf.example" >"$nonroot_output" 2>&1; then
  fail "start wrapper ran as non-root"
fi
grep -q 'requires root' "$nonroot_output" || fail "non-root start refusal was not explicit"

wrong_config=$tmp_dir/wrong-target.conf
sed 's/^SALVAGEHOST_USB_VM_NAME=nodehost-dev$/SALVAGEHOST_USB_VM_NAME=other-vm/' \
  "$script_dir/usb-device.conf.example" > "$wrong_config"
if "$script_dir/start-nodehost-dev-with-usb.sh" --config "$wrong_config" >"$tmp_dir/wrong-target.out" 2>&1; then
  fail "start wrapper accepted a wrong VM target"
fi
grep -q 'only nodehost-dev is supported' "$tmp_dir/wrong-target.out" || fail "wrong-target refusal was not explicit"

fake_proc=$tmp_dir/proc/123
mkdir -p "$fake_proc"
printf 'adb\n' > "$fake_proc/comm"
adb_config=$tmp_dir/adb-config.conf
sed \
  -e "s#^SALVAGEHOST_USB_LOCK_FILE=.*#SALVAGEHOST_USB_LOCK_FILE=$tmp_dir/adb.lock#" \
  -e "s#^SALVAGEHOST_USB_STATE_DIR=.*#SALVAGEHOST_USB_STATE_DIR=$tmp_dir/adb-state#" \
  "$script_dir/usb-device.conf.example" > "$adb_config"
if SALVAGEHOST_USB_PROC_ROOT="$tmp_dir/proc" \
  "$script_dir/reconcile-usb-device.sh" --check \
  --config "$adb_config" >"$tmp_dir/adb.out" 2>&1; then
  fail "reconciler accepted a competing adb process"
fi
grep -q 'competing ADB process detected' "$tmp_dir/adb.out" || fail "competing ADB refusal was not explicit"
grep -q '"$reconciler" --preflight' "$script_dir/start-nodehost-dev-with-usb.sh" || fail "start wrapper does not use the strict preflight gate"

grep -q 'ConditionPathExists=/run/salvagehost/nodehost-dev-usb.active' \
  "$script_dir/systemd/salvagehost-usb-reconcile.service" || fail "event service is not session-gated"
grep -q 'ExecStart=/usr/local/libexec/salvagehost/usb-session-monitor.py' \
  "$script_dir/systemd/salvagehost-usb-reconcile.service" || fail "event service does not start the monitor"
grep -q '^ProtectSystem=strict$' \
  "$script_dir/systemd/salvagehost-usb-reconcile.service" || fail "event service lost strict filesystem protection"
grep -q '^ReadWritePaths=.*\(/run/udev/rules\.d\)\( \|$\)' \
  "$script_dir/systemd/salvagehost-usb-reconcile.service" || fail "event service cannot clean the transient udev rule"
grep -q 'manual-only' "$script_dir/systemd/salvagehost-usb-reconcile.timer" || fail "legacy timer is not marked manual-only"
if grep -Eq 'WantedBy=timers\.target|systemctl (enable|start)' "$script_dir/systemd/salvagehost-usb-reconcile.timer"; then
  fail "legacy timer fixture exposes an enablement path"
fi

line_of() {
  grep -nF -- "$1" "$script_dir/start-nodehost-dev-with-usb.sh" | head -n 1 | cut -d: -f1
}

activate_line=$(line_of '"$reconciler" --activate-session --config "$config_file"')
detach_line=$(line_of '"$reconciler" --detach-persistent --config "$config_file"')
preflight_line=$(line_of '"$reconciler" --preflight --config "$config_file"')
vm_start_line=$(line_of 'virsh -c qemu:///system start nodehost-dev >/dev/null')
apply_line=$(line_of '"$reconciler" --apply --config "$config_file"')
monitor_start_line=$(line_of 'systemctl start "$monitor_service"')
[[ -n $activate_line && -n $detach_line && -n $preflight_line && -n $vm_start_line && -n $apply_line && -n $monitor_start_line ]] \
  || fail "start wrapper is missing a required lifecycle step"
(( activate_line < detach_line && detach_line < preflight_line && preflight_line < vm_start_line && vm_start_line < apply_line && apply_line < monitor_start_line )) \
  || fail "start wrapper starts the monitor before the initial live USB attach completes"
grep -q 'refusing to start event monitor while VM is' \
  "$script_dir/start-nodehost-dev-with-usb.sh" || fail "start wrapper does not gate monitor startup on a running VM"

echo "USB reconciler validation passed (repository-only; no host mutations performed)"
