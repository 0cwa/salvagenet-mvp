#!/bin/sh
set -eu
mkdir -p /var/lib/nodehost

has_filesystem() {
  grep -qw "$1" /proc/filesystems 2>/dev/null
}
has_module_or_builtin() {
  test -d "/sys/module/$1" || modprobe -n "$1" >/dev/null 2>&1
}
json_bool() {
  "$@" >/dev/null 2>&1 && printf true || printf false
}
has_namespaces() {
  for ns in mnt net pid ipc uts cgroup; do
    test -e "/proc/self/ns/$ns" || return 1
  done
}
has_packet_filter() {
  command -v nft >/dev/null 2>&1 || command -v iptables >/dev/null 2>&1
}
tailscale_reachable() {
  command -v tailscale >/dev/null 2>&1 && tailscale status --json >/dev/null 2>&1
}

cat <<JSON
{
  "schemaVersion": 1,
  "profile": "k3s-worker-lab",
  "checks": {
    "cgroupV2": $(test -f /sys/fs/cgroup/cgroup.controllers && printf true || printf false),
    "namespaces": $(json_bool has_namespaces),
    "overlayfs": $(json_bool has_filesystem overlay),
    "brNetfilter": $(json_bool has_module_or_builtin br_netfilter),
    "vxlan": $(json_bool has_module_or_builtin vxlan),
    "tun": $(test -c /dev/net/tun && printf true || printf false),
    "iptablesOrNft": $(json_bool has_packet_filter),
    "ipForwarding": $(test "$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null || echo 0)" = 1 && printf true || printf false),
    "swapDisabled": $(test "$(awk 'NR>1{n++} END{print n+0}' /proc/swaps)" = 0 && printf true || printf false),
    "tailscaleReachable": $(json_bool tailscale_reachable),
    "memoryMiB": $(awk '/MemTotal/{printf "%d", $2/1024}' /proc/meminfo),
    "rootFreeMiB": $(df -Pm / | awk 'NR==2{print $4}')
  },
  "joinedCluster": false
}
JSON
