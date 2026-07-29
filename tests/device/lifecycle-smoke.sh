#!/usr/bin/env bash
set -euo pipefail
package=${NODEHOST_PACKAGE:-com.excp.podroid.debug}
adb shell am force-stop "$package"
adb shell monkey -p "$package" -c android.intent.category.LAUNCHER 1 >/dev/null
printf 'manual follow-up required: verify desired runtime reconciles and exactly one QEMU process exists.
'
