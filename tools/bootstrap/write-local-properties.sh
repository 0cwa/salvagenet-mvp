#!/usr/bin/env bash
set -euo pipefail
: "${ANDROID_SDK_ROOT:?source ~/.config/nodehost/env.sh first}"
[[ -d android/podroid ]] || { echo "import Podroid first" >&2; exit 2; }
printf 'sdk.dir=%s
' "${ANDROID_SDK_ROOT//\/\\}" > android/podroid/local.properties
