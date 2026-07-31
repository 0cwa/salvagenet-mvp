#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"
exec python3 "$root/lab/qemu/scripts/h02a-prepare.py" \
  --state "$state" \
  --ssh-port "$ssh_port"
