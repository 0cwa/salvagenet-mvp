#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"

success=false
evidence_path=
cleanup_on_failure() {
  local rc=$?
  trap - EXIT INT TERM
  if [[ $success != true ]]; then
    "$(dirname "$0")/stop.sh" >/dev/null 2>&1 || true
    echo "H02A failed; diagnostic state retained under $state" >&2
  fi
  exit "$rc"
}
trap cleanup_on_failure EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"$(dirname "$0")/stop.sh" >/dev/null 2>&1 || true
"$(dirname "$0")/prepare.sh"
"$(dirname "$0")/start.sh"
"$(dirname "$0")/smoke.sh" initial
initial_boot=$(cat "$state/boot-id-initial.txt")

ssh_nodeadmin 15 'sudo -n systemctl reboot' >/dev/null 2>&1 || true
wait_for_ssh_down 90
wait_for_ssh 360
"$(dirname "$0")/smoke.sh" guest-reboot
guest_reboot=$(cat "$state/boot-id-guest-reboot.txt")
[[ $guest_reboot != "$initial_boot" ]] || {
  echo "guest reboot did not change the boot ID" >&2
  exit 1
}

ssh_nodeadmin 15 'sudo -n systemctl poweroff' >/dev/null 2>&1 || true
wait_for_ssh_down 90 || true
wait_for_qemu_exit 180
"$(dirname "$0")/start.sh"
"$(dirname "$0")/smoke.sh" qemu-restart
qemu_restart=$(cat "$state/boot-id-qemu-restart.txt")
[[ $qemu_restart != "$guest_reboot" && $qemu_restart != "$initial_boot" ]] || {
  echo "complete QEMU stop/start did not produce a distinct boot ID" >&2
  exit 1
}

evidence_path=$(python3 "$root/lab/qemu/scripts/h02a-evidence.py" create --state "$state")
"$(dirname "$0")/stop.sh" --cleanup --evidence "$evidence_path"
python3 "$root/lab/qemu/scripts/h02a-evidence.py" finalize-cleanup \
  --state "$state" \
  --evidence "$evidence_path"
success=true
printf 'H02A host-QEMU qualification: PASS\nevidence=%s\n' "$evidence_path"
