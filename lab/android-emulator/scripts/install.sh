#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -ne 0 ]] || { echo "run as the development user, not root" >&2; exit 2; }
: "${ANDROID_SDK_ROOT:?source ~/.config/nodehost/env.sh first}"
command -v sdkmanager >/dev/null || { echo "sdkmanager missing" >&2; exit 2; }
command -v avdmanager >/dev/null || { echo "avdmanager missing" >&2; exit 2; }

case $(uname -m) in
  x86_64|amd64) abi=x86_64 ;;
  aarch64|arm64) abi=arm64-v8a ;;
  *) echo "unsupported emulator host architecture: $(uname -m)" >&2; exit 2 ;;
esac
package="system-images;android-36;google_apis;$abi"
name=${NODEHOST_AVD_NAME:-nodehost-api36}

yes | sdkmanager --licenses >/dev/null
sdkmanager "emulator" "$package"
if ! avdmanager list avd | grep -Fq "Name: $name"; then
  printf 'no\n' | avdmanager create avd --force --name "$name" --package "$package" --device pixel_6
fi

config="$HOME/.android/avd/${name}.avd/config.ini"
if [[ -f "$config" ]]; then
  grep -q '^hw.ramSize=' "$config" && sed -i 's/^hw.ramSize=.*/hw.ramSize=3072/' "$config" || echo 'hw.ramSize=3072' >> "$config"
  grep -q '^disk.dataPartition.size=' "$config" && sed -i 's/^disk.dataPartition.size=.*/disk.dataPartition.size=8G/' "$config" || echo 'disk.dataPartition.size=8G' >> "$config"
fi
printf 'installed AVD %s using %s\n' "$name" "$package"
