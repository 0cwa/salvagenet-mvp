#!/usr/bin/env bash
set -euo pipefail

script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
if [[ $EUID -ne 0 ]]; then
  if command -v run0 >/dev/null; then
    exec run0 -i "$script_path" "$@"
  elif command -v sudo >/dev/null; then
    exec sudo -- "$script_path" "$@"
  else
    echo "requires root; rerun as root or install run0 or sudo" >&2
    exit 2
  fi
fi

lab_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
env_file=$lab_dir/.env

[[ -f $env_file ]] || {
  echo "missing $env_file; copy .env.example first" >&2
  exit 2
}

# This is a local, user-controlled configuration file. Do not echo it, and do
# not add secret-bearing variables to cloud-init, libvirt XML, or command args.
# shellcheck disable=SC1090
source "$env_file"

: "${SALVAGEHOST_VM_NAME:?}"
: "${SALVAGEHOST_VM_MEMORY_MIB:?}"
: "${SALVAGEHOST_VM_VCPUS:?}"
: "${SALVAGEHOST_VM_DISK_GIB:?}"
: "${SALVAGEHOST_REPOSITORY:?}"
: "${SALVAGEHOST_SSH_PUBLIC_KEY:?}"
[[ -d $SALVAGEHOST_REPOSITORY ]] || { echo "repository not found" >&2; exit 2; }
[[ -f $SALVAGEHOST_SSH_PUBLIC_KEY ]] || { echo "SSH public key not found" >&2; exit 2; }

for command in curl qemu-img sha256sum virt-install virsh virtiofsd; do
  command -v "$command" >/dev/null || { echo "missing $command" >&2; exit 2; }
done

image_url=${SALVAGEHOST_UBUNTU_IMAGE_URL:-https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img}
image_name=${image_url##*/}
image_base=${image_url%/*}
state_dir=$lab_dir/.state
image_dir=/var/lib/libvirt/images/$SALVAGEHOST_VM_NAME
base_image=$image_dir/$image_name
disk_image=$image_dir/$SALVAGEHOST_VM_NAME.qcow2
checksum_file=$image_dir/SHA256SUMS

install -d -m 0755 "$image_dir" /var/lib/libvirt/boot "$state_dir"
[[ -f $base_image ]] || curl --fail --location --retry 3 --output "$base_image" "$image_url"

if [[ -n ${SALVAGEHOST_UBUNTU_IMAGE_SHA256:-} ]]; then
  expected=$SALVAGEHOST_UBUNTU_IMAGE_SHA256
else
  curl --fail --location --retry 3 --output "$checksum_file" "$image_base/SHA256SUMS"
  expected=$(awk -v name="$image_name" '$2 == name { print $1; exit }' "$checksum_file")
fi
[[ -n $expected ]] || { echo "no SHA-256 for $image_name" >&2; exit 2; }
actual=$(sha256sum "$base_image" | awk '{print $1}')
[[ $actual == "$expected" ]] || { echo "Ubuntu image checksum mismatch" >&2; exit 1; }
printf 'SALVAGEHOST_UBUNTU_IMAGE_URL=%q\nSALVAGEHOST_UBUNTU_IMAGE_SHA256=%q\n' "$image_url" "$actual" > "$state_dir/resolved-image.env"

if ! virsh -c qemu:///system dominfo "$SALVAGEHOST_VM_NAME" >/dev/null 2>&1; then
  [[ -f $disk_image ]] || qemu-img create -f qcow2 -F qcow2 -b "$base_image" "$disk_image" "${SALVAGEHOST_VM_DISK_GIB}G"
  network_args=(--network 'network=default,model.type=virtio')
  if [[ -n ${SALVAGEHOST_DIRECT_INTERFACE:-} ]]; then
    network_args+=(--network "type=direct,source=$SALVAGEHOST_DIRECT_INTERFACE,source.mode=bridge,model.type=virtio")
  fi
  virt-install --connect qemu:///system --name "$SALVAGEHOST_VM_NAME" \
    --memory "$SALVAGEHOST_VM_MEMORY_MIB" --memorybacking access.mode=shared \
    --vcpus "$SALVAGEHOST_VM_VCPUS" --cpu host-passthrough --import \
    --osinfo detect=on,require=off \
    --disk "path=$disk_image,format=qcow2,bus=virtio,discard=unmap" \
    "${network_args[@]}" \
    --filesystem "source=$SALVAGEHOST_REPOSITORY,target=salvagenet,accessmode=passthrough,driver.type=virtiofs" \
    --cloud-init "user-data=$lab_dir/cloud-init/user-data.yaml,clouduser-ssh-key=$SALVAGEHOST_SSH_PUBLIC_KEY" \
    --graphics spice --video virtio \
    --channel unix,target.type=virtio,target.name=org.qemu.guest_agent.0 \
    --noautoconsole
fi

virsh -c qemu:///system dominfo "$SALVAGEHOST_VM_NAME"
