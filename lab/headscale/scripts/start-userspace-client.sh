#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 <name> <authkey-file> <socks-port>" >&2; exit 2; }
name=$1; keyfile=$2; port=$3
command -v tailscaled >/dev/null || { echo "tailscaled not installed" >&2; exit 1; }
url=$(awk -F= '$1=="HEADSCALE_PUBLIC_URL"{print $2}' "$(dirname "$0")/../.env")
state="$(dirname "$0")/../.state/$name"; mkdir -p "$state"
tailscaled --tun=userspace-networking --state="$state/state" --socket="$state/socket" --socks5-server="localhost:$port" >"$state/tailscaled.log" 2>&1 & echo $! >"$state/pid"
tailscale --socket="$state/socket" up --login-server "$url" --auth-key "$(cat "$keyfile")" --hostname "$name"
