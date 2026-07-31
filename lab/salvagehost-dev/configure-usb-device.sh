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
dry_run=false

if [[ ${1:-} == --dry-run ]]; then
  dry_run=true
elif [[ $# -ne 0 ]]; then
  echo "usage: $0 [--dry-run]" >&2
  exit 2
fi

[[ -f $env_file ]] || { echo "missing $env_file; copy .env.example first" >&2; exit 2; }
# This local file may contain credentials. Never echo it or put it in XML.
# shellcheck disable=SC1090
source "$env_file"

: "${SALVAGEHOST_VM_NAME:?}"
: "${SALVAGEHOST_USB_VENDOR_ID:?set the USB vendor ID in .env}"
: "${SALVAGEHOST_USB_PRODUCT_ID:?set the USB product ID in .env}"
: "${SALVAGEHOST_USB_STARTUP_POLICY:=optional}"

for id in "$SALVAGEHOST_USB_VENDOR_ID" "$SALVAGEHOST_USB_PRODUCT_ID"; do
  [[ $id =~ ^[[:xdigit:]]{4}$ ]] || { echo "USB IDs must be four hexadecimal digits" >&2; exit 2; }
done
case $SALVAGEHOST_USB_STARTUP_POLICY in mandatory|requisite|optional) ;; *)
  echo "USB startup policy must be mandatory, requisite, or optional" >&2
  exit 2
esac

xml=$(mktemp)
trap 'rm -f "$xml"' EXIT
cat > "$xml" <<EOF
<hostdev mode='subsystem' type='usb'>
  <source startupPolicy='$SALVAGEHOST_USB_STARTUP_POLICY'>
    <vendor id='0x${SALVAGEHOST_USB_VENDOR_ID,,}'/>
    <product id='0x${SALVAGEHOST_USB_PRODUCT_ID,,}'/>
  </source>
</hostdev>
EOF

if $dry_run; then
  cat "$xml"
  exit 0
fi

if virsh -c qemu:///system dumpxml "$SALVAGEHOST_VM_NAME" | grep -Fq "id='0x${SALVAGEHOST_USB_VENDOR_ID,,}'" \
  && virsh -c qemu:///system dumpxml "$SALVAGEHOST_VM_NAME" | grep -Fq "id='0x${SALVAGEHOST_USB_PRODUCT_ID,,}'"; then
  echo "USB host device is already configured for $SALVAGEHOST_VM_NAME"
  exit 0
fi

state=$(virsh -c qemu:///system domstate "$SALVAGEHOST_VM_NAME")
if [[ $state == running ]]; then
  virsh -c qemu:///system attach-device "$SALVAGEHOST_VM_NAME" "$xml" --live --config
else
  virsh -c qemu:///system attach-device "$SALVAGEHOST_VM_NAME" "$xml" --config
fi
echo "USB host device configured for $SALVAGEHOST_VM_NAME"
