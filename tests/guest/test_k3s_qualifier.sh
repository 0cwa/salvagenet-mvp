#!/usr/bin/env bash
set -euo pipefail
script=profiles/guest-init/k3s-worker-lab/qualify-k3s.sh
sh -n "$script"
grep -q '"joinedCluster": false' "$script"
! grep -Eq 'k3s (server|agent)|curl.*get.k3s.io' "$script"
printf 'k3s qualifier static checks: PASS
'
