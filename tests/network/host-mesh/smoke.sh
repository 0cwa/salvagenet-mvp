#!/usr/bin/env bash
set -euo pipefail

# TODO(RESEARCH, T05): install the APK, grant VPN permission interactively, and
# verify that the embedded host node appears in the local Headscale lab.
printf '%s\n' 'SKIP: requires an authorized Android device and completed T05 mesh adapter'
exit 77
