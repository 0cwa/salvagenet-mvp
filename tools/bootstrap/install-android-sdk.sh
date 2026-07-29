#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -ne 0 ]] || { echo "run as the development user, not root" >&2; exit 2; }

case $(uname -m) in
  x86_64|amd64) ;;
  *) echo "WARN: Google's Linux Android SDK host binaries are primarily qualified on x86_64; detected $(uname -m)" >&2 ;;
esac

SDK_ROOT=${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}
TOOLS_REV=15859902
TOOLS_SHA256=4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583
URL="https://dl.google.com/android/repository/commandlinetools-linux-${TOOLS_REV}_latest.zip"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$SDK_ROOT/cmdline-tools" "$HOME/.config/nodehost"

if [[ ! -x "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" ]]; then
  curl --fail --location --output "$tmp/tools.zip" "$URL"
  echo "$TOOLS_SHA256  $tmp/tools.zip" | sha256sum -c -
  unzip -q "$tmp/tools.zip" -d "$tmp/unpack"
  rm -rf "$SDK_ROOT/cmdline-tools/latest"
  mv "$tmp/unpack/cmdline-tools" "$SDK_ROOT/cmdline-tools/latest"
fi

java_home=${NODEHOST_JAVA_HOME:-}
if [[ -z "$java_home" ]]; then
  for candidate in /usr/lib/jvm/java-17-openjdk-* /usr/lib/jvm/temurin-17-* /usr/lib/jvm/temurin-17*; do
    if [[ -x "$candidate/bin/javac" ]]; then
      java_home=$candidate
      break
    fi
  done
fi
if [[ -z "$java_home" || ! -x "$java_home/bin/javac" ]]; then
  echo "JDK 17 not found; run sudo tools/bootstrap/ubuntu-root-setup.sh or set NODEHOST_JAVA_HOME" >&2
  exit 2
fi
if [[ $("$java_home/bin/javac" -version 2>&1) != javac\ 17* ]]; then
  echo "NODEHOST_JAVA_HOME must point to JDK 17: $java_home" >&2
  exit 2
fi

cat > "$HOME/.config/nodehost/android-env.sh" <<ENV
export ANDROID_SDK_ROOT="$SDK_ROOT"
export ANDROID_HOME="$SDK_ROOT"
export JAVA_HOME="$java_home"
export PATH="\$JAVA_HOME/bin:\$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:\$ANDROID_SDK_ROOT/platform-tools:\$PATH"
ENV
cat > "$HOME/.config/nodehost/env.sh" <<'ENV'
# Generated dispatcher. Individual installers own their own fragments.
for nodehost_fragment in \
  "$HOME/.config/nodehost/go-env.sh" \
  "$HOME/.config/nodehost/android-env.sh"; do
  if [[ -f "$nodehost_fragment" ]]; then
    # shellcheck disable=SC1090
    source "$nodehost_fragment"
  fi
done
unset nodehost_fragment
ENV
# shellcheck disable=SC1090,SC1091
source "$HOME/.config/nodehost/env.sh"
yes | sdkmanager --licenses >/dev/null
sdkmanager \
  "platform-tools" \
  "platforms;android-36" \
  "build-tools;36.0.0" \
  "ndk;27.2.12479018" \
  "cmake;3.22.1"
printf 'Android SDK installed at %s\nsource %s/.config/nodehost/env.sh\n' "$SDK_ROOT" "$HOME"
