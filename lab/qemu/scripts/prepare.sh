#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"
for command in qemu-system-aarch64 qemu-img cloud-localds ssh-keygen; do
  command -v "$command" >/dev/null || { echo "missing $command" >&2; exit 2; }
done

base="$state/noble-server-cloudimg-arm64.img"
"$root/tools/profiles/pin-ubuntu-image.sh" "$base"
qemu-img create -f qcow2 -F qcow2 -b "$base" "$state/system.qcow2" >/dev/null

if [[ ! -f "$state/id_ed25519" ]]; then
  ssh-keygen -q -t ed25519 -N '' -C nodehost-qemu-lab -f "$state/id_ed25519"
fi
public_key=$(cat "$state/id_ed25519.pub")
cat > "$state/meta-data" <<EOF
instance-id: nodehost-qemu-lab
local-hostname: nodehost-qemu-lab
EOF
cat > "$state/user-data" <<EOF
#cloud-config
users:
  - name: nodeadmin
    groups: [sudo]
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: true
    ssh_authorized_keys:
      - $public_key
ssh_pwauth: false
disable_root: true
packages: [openssh-server, ca-certificates, curl, jq]
runcmd:
  - [sh, -c, 'mkdir -p /var/lib/nodehost && printf ready > /var/lib/nodehost/host-qemu-ready']
EOF
cloud-localds "$state/seed.img" "$state/user-data" "$state/meta-data"

code=$(find_firmware code) || { echo "AArch64 UEFI code firmware not found" >&2; exit 2; }
vars=$(find_firmware vars) || { echo "AArch64 UEFI variable template not found" >&2; exit 2; }
cp "$code" "$state/AAVMF_CODE.fd"
cp "$vars" "$state/AAVMF_VARS.fd"
printf 'prepared host-QEMU lab in %s\n' "$state"
