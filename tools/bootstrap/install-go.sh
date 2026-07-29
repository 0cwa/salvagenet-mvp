#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -ne 0 ]] || { echo "run as the development user, not root" >&2; exit 2; }

GO_VERSION=1.26.3
case $(uname -m) in
  x86_64|amd64)
    GO_ARCH=amd64
    GO_SHA256=2b2cfc7148493da5e73981bffbf3353af381d5f93e789c82c79aff64962eb556
    ;;
  aarch64|arm64)
    GO_ARCH=arm64
    GO_SHA256=9d89a3ea57d141c2b22d70083f2c8459ba3890f2d9e818e7e933b75614936565
    ;;
  *)
    echo "unsupported Go host architecture: $(uname -m)" >&2
    exit 2
    ;;
esac

prefix=${NODEHOST_GO_ROOT:-$HOME/.local/nodehost/go/$GO_VERSION}
archive="go${GO_VERSION}.linux-${GO_ARCH}.tar.gz"
url="https://go.dev/dl/${archive}"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$(dirname "$prefix")" "$HOME/.config/nodehost"

if [[ ! -x "$prefix/bin/go" ]] || [[ $("$prefix/bin/go" version 2>/dev/null || true) != "go version go${GO_VERSION} linux/${GO_ARCH}" ]]; then
  curl --fail --location --output "$tmp/$archive" "$url"
  echo "$GO_SHA256  $tmp/$archive" | sha256sum -c -
  rm -rf "$prefix"
  mkdir -p "$prefix"
  tar -xzf "$tmp/$archive" --strip-components=1 -C "$prefix"
fi

cat > "$HOME/.config/nodehost/go-env.sh" <<ENV
export GOROOT="$prefix"
export GOPATH="\${GOPATH:-\$HOME/go}"
export PATH="\$GOROOT/bin:\$GOPATH/bin:\$PATH"
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
go version
printf 'Go %s installed at %s\nsource %s/.config/nodehost/env.sh\n' "$GO_VERSION" "$prefix" "$HOME"
