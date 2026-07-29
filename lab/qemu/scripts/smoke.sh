#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"
[[ -f "$state/id_ed25519" ]] || { echo "missing lab key" >&2; exit 2; }
for _ in $(seq 1 240); do
  if ssh -q \
      -o BatchMode=yes \
      -o StrictHostKeyChecking=no \
      -o UserKnownHostsFile=/dev/null \
      -o ConnectTimeout=2 \
      -i "$state/id_ed25519" \
      -p "$ssh_port" nodeadmin@127.0.0.1 \
      'test -f /var/lib/nodehost/host-qemu-ready'; then
    echo "host-QEMU Ubuntu/cloud-init/SSH smoke: PASS"
    exit 0
  fi
  sleep 2
done
echo "host-QEMU smoke timed out; inspect $state/serial.log" >&2
exit 1
