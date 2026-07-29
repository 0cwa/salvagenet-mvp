#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
state=${NODEHOST_QEMU_LAB_DIR:-$root/.local/qemu-lab}
ssh_port=${NODEHOST_QEMU_LAB_SSH_PORT:-2222}
export root state ssh_port
mkdir -p "$state"

find_firmware() {
  local kind=$1 candidate
  if [[ $kind == code ]]; then
    for candidate in \
      /usr/share/AAVMF/AAVMF_CODE.fd \
      /usr/share/AAVMF/AAVMF_CODE.ms.fd \
      /usr/share/qemu-efi-aarch64/QEMU_EFI.fd; do
      [[ -f $candidate ]] && { printf '%s\n' "$candidate"; return 0; }
    done
  else
    for candidate in \
      /usr/share/AAVMF/AAVMF_VARS.fd \
      /usr/share/AAVMF/AAVMF_VARS.ms.fd; do
      [[ -f $candidate ]] && { printf '%s\n' "$candidate"; return 0; }
    done
  fi
  return 1
}
