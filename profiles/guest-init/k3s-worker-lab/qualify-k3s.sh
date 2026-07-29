#!/bin/sh
set -eu

output_path=${1:-}
if test -n "$output_path"; then
  case "$output_path" in
    /*) ;;
    *) echo "qualification output path must be absolute" >&2; exit 2 ;;
  esac
  temporary=$(mktemp "${output_path}.tmp.XXXXXX")
else
  temporary=$(mktemp "${TMPDIR:-/tmp}/nodehost-k3s-qualification.XXXXXX")
fi
trap 'rm -f "$temporary"' EXIT HUP INT TERM

has_filesystem() {
  grep -qw "$1" /proc/filesystems 2>/dev/null
}
has_module_or_builtin() {
  test -d "/sys/module/$1" || { command -v modprobe >/dev/null 2>&1 && modprobe -n "$1" >/dev/null 2>&1; }
}
check_bool() {
  if "$@" >/dev/null 2>&1; then printf true; else printf false; fi
}
has_namespaces() {
  for namespace in mnt net pid ipc uts cgroup; do
    test -e "/proc/self/ns/$namespace" || return 1
  done
}
has_packet_filter() {
  command -v nft >/dev/null 2>&1 || command -v iptables >/dev/null 2>&1
}
has_supported_kernel() {
  major=$(uname -r | cut -d. -f1)
  test "$major" -ge 5 2>/dev/null
}
tailscale_reachable() {
  command -v tailscale >/dev/null 2>&1 \
    && timeout 5 tailscale status --json >/dev/null 2>&1
}

kernel_release=$(uname -r)
kernel_supported=$(check_bool has_supported_kernel)
cgroup_v2=$(test -f /sys/fs/cgroup/cgroup.controllers && printf true || printf false)
namespaces=$(check_bool has_namespaces)
overlayfs=$(check_bool has_filesystem overlay)
br_netfilter=$(check_bool has_module_or_builtin br_netfilter)
vxlan=$(check_bool has_module_or_builtin vxlan)
tun=$(test -c /dev/net/tun && printf true || printf false)
packet_filter=$(check_bool has_packet_filter)
ip_forwarding=$(test "$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null || echo 0)" = 1 && printf true || printf false)
swap_disabled=$(test "$(awk 'NR>1{n++} END{print n+0}' /proc/swaps)" = 0 && printf true || printf false)
tailscale=$(check_bool tailscale_reachable)
memory_mib=$(awk '/MemTotal/{printf "%d", $2/1024}' /proc/meminfo)
root_total_mib=$(df -Pm / | awk 'NR==2{print $2}')
root_free_mib=$(df -Pm / | awk 'NR==2{print $4}')
minimum_memory=$(test "$memory_mib" -ge 1024 && printf true || printf false)
minimum_storage=$(test "$root_total_mib" -ge 8192 && printf true || printf false)

outcome=qualified
for required in "$kernel_supported" "$cgroup_v2" "$namespaces" "$overlayfs" \
  "$tun" "$packet_filter" "$minimum_memory" "$minimum_storage"; do
  if test "$required" != true; then outcome=unsupported; break; fi
done
if test "$outcome" = qualified; then
  for recommended in "$br_netfilter" "$vxlan" "$ip_forwarding" \
    "$swap_disabled" "$tailscale"; do
    if test "$recommended" != true; then outcome=qualified-with-warnings; break; fi
  done
fi

jq -n \
  --arg profile k3s-worker-lab \
  --arg outcome "$outcome" \
  --arg kernelRelease "$kernel_release" \
  --argjson kernelSupported "$kernel_supported" \
  --argjson cgroupV2 "$cgroup_v2" \
  --argjson namespaces "$namespaces" \
  --argjson overlayfs "$overlayfs" \
  --argjson brNetfilter "$br_netfilter" \
  --argjson vxlan "$vxlan" \
  --argjson tun "$tun" \
  --argjson iptablesOrNft "$packet_filter" \
  --argjson ipForwarding "$ip_forwarding" \
  --argjson swapDisabled "$swap_disabled" \
  --argjson tailscaleReachable "$tailscale" \
  --argjson memoryMiB "$memory_mib" \
  --argjson rootTotalMiB "$root_total_mib" \
  --argjson rootFreeMiB "$root_free_mib" \
  --argjson minimumMemory "$minimum_memory" \
  --argjson minimumStorage "$minimum_storage" \
  '{
    schemaVersion: 1,
    profile: $profile,
    outcome: $outcome,
    checks: {
      kernelRelease: $kernelRelease,
      kernelSupported: $kernelSupported,
      cgroupV2: $cgroupV2,
      namespaces: $namespaces,
      overlayfs: $overlayfs,
      brNetfilter: $brNetfilter,
      vxlan: $vxlan,
      tun: $tun,
      iptablesOrNft: $iptablesOrNft,
      ipForwarding: $ipForwarding,
      swapDisabled: $swapDisabled,
      tailscaleReachable: $tailscaleReachable,
      memoryMiB: $memoryMiB,
      rootTotalMiB: $rootTotalMiB,
      rootFreeMiB: $rootFreeMiB,
      minimumMemory: $minimumMemory,
      minimumStorage: $minimumStorage
    },
    joinedCluster: false
  }' > "$temporary"

if test "$(wc -c < "$temporary")" -gt 4096; then
  echo "qualification report exceeded 4096 bytes" >&2
  exit 1
fi
jq -e '.schemaVersion == 1 and .joinedCluster == false' "$temporary" >/dev/null
chmod 0600 "$temporary"
if test -n "$output_path"; then
  mv -f "$temporary" "$output_path"
  trap - EXIT HUP INT TERM
else
  cat "$temporary"
fi
