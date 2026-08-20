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
state_dir=$lab_dir/.state
state_file=$state_dir/lan-forward.env
dry_run=false

if [[ ${1:-} == --dry-run ]]; then
  dry_run=true
elif [[ $# -ne 0 ]]; then
  echo "usage: $0 [--dry-run]" >&2
  exit 2
fi

[[ -f $env_file ]] || { echo "missing $env_file; copy .env.example first" >&2; exit 2; }
# This local file may contain credentials. Never echo it or pass it to the
# firewall, libvirt, cloud-init, or command-line arguments.
# shellcheck disable=SC1090
source "$env_file"

: "${SALVAGEHOST_VM_NAME:?}"
: "${SALVAGEHOST_LAN_FORWARD_PORT:?set the host LAN port in .env}"
: "${SALVAGEHOST_GUEST_FORWARD_PORT:?set the guest port in .env}"
: "${SALVAGEHOST_LIBVIRT_NETWORK:=default}"

for port in "$SALVAGEHOST_LAN_FORWARD_PORT" "$SALVAGEHOST_GUEST_FORWARD_PORT"; do
  [[ $port =~ ^[0-9]+$ && $port -ge 1 && $port -le 65535 ]] || {
    echo "forward ports must be between 1 and 65535" >&2
    exit 2
  }
done

if [[ -n ${SALVAGEHOST_LAN_INTERFACE:-} ]]; then
  lan_interface=$SALVAGEHOST_LAN_INTERFACE
else
  lan_interface=$(ip route show default | awk '/^default/ { print $5; exit }')
fi
[[ -n $lan_interface ]] || { echo "could not determine the host LAN interface" >&2; exit 1; }

zone=$(firewall-cmd --get-zone-of-interface="$lan_interface")
[[ -n $zone ]] || { echo "no firewalld zone owns $lan_interface" >&2; exit 1; }

vm_mac=$(virsh -c qemu:///system domiflist "$SALVAGEHOST_VM_NAME" |
  awk -v network="$SALVAGEHOST_LIBVIRT_NETWORK" '$2 == "network" && $3 == network { print $5; exit }')
[[ -n $vm_mac ]] || {
  echo "no $SALVAGEHOST_LIBVIRT_NETWORK NIC found for $SALVAGEHOST_VM_NAME" >&2
  exit 1
}
vm_ip=$(virsh -c qemu:///system net-dhcp-leases "$SALVAGEHOST_LIBVIRT_NETWORK" |
  awk -v mac="$vm_mac" 'tolower($3) == tolower(mac) { sub(/\/.*/, "", $5); print $5; exit }')
[[ $vm_ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || {
  echo "no IPv4 DHCP lease for $SALVAGEHOST_VM_NAME on $SALVAGEHOST_LIBVIRT_NETWORK; start the VM and retry" >&2
  exit 1
}

forward="port=$SALVAGEHOST_LAN_FORWARD_PORT:proto=tcp:toaddr=$vm_ip:toport=$SALVAGEHOST_GUEST_FORWARD_PORT"
old_forward=
if [[ -f $state_file ]]; then
  # The file is generated locally by this script and contains no credentials.
  # shellcheck disable=SC1090
  source "$state_file"
  old_forward=${SALVAGEHOST_LAN_FORWARD_RULE:-}
fi

if $dry_run; then
  printf 'LAN interface: %s\nFirewalld zone: %s\nVM NAT address: %s\nForward: %s\n' \
    "$lan_interface" "$zone" "$vm_ip" "$forward"
  exit 0
fi

if [[ -n $old_forward && $old_forward != "$forward" ]]; then
  firewall-cmd --zone="$zone" --remove-forward-port="$old_forward" || true
  firewall-cmd --permanent --zone="$zone" --remove-forward-port="$old_forward" || true
fi

if firewall-cmd --zone="$zone" --query-forward-port="$forward"; then
  :
else
  conflicting=$(firewall-cmd --zone="$zone" --list-forward-ports |
    awk -v port="$SALVAGEHOST_LAN_FORWARD_PORT" '$0 ~ "(^| )port=" port ":proto=tcp(:|$)" { print }')
  [[ -z $conflicting ]] || {
    echo "refusing to replace an unowned forward on $zone: $conflicting" >&2
    exit 1
  }
  firewall-cmd --zone="$zone" --add-forward-port="$forward"
fi

if ! firewall-cmd --permanent --zone="$zone" --query-forward-port="$forward"; then
  firewall-cmd --permanent --zone="$zone" --add-forward-port="$forward"
fi

install -d -m 0700 "$state_dir"
umask 077
printf 'SALVAGEHOST_LAN_FORWARD_RULE=%q\nSALVAGEHOST_LAN_FORWARD_ZONE=%q\n' "$forward" "$zone" > "$state_file"
echo "forwarding $lan_interface:$SALVAGEHOST_LAN_FORWARD_PORT to $SALVAGEHOST_VM_NAME ($vm_ip):$SALVAGEHOST_GUEST_FORWARD_PORT"
