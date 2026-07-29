#!/usr/bin/env bash
set -euo pipefail

# Reproducibly builds the official Android-aware libtailscale binding pinned by
# android/vendor/tailscale/tailscale.lock. Generated sources and binaries stay ignored.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
lock="$repo_root/android/vendor/tailscale/tailscale.lock"
build_root="$repo_root/android/vendor/tailscale/build"
src="$build_root/tailscale-android"
out="$build_root/libtailscale.aar"
provenance="$build_root/libtailscale.provenance"

read_lock() {
  python3 - "$lock" "$1" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    print(json.load(f)[sys.argv[2]])
PY
}

android_repository="$(read_lock repository)"
android_commit="$(read_lock commit)"
core_ref="$(read_lock coreRef)"
core_commit="$(read_lock coreCommit)"
required_go="$(read_lock requiredGo)"

actual_go="$(go env GOVERSION)"
if [[ "$actual_go" != "go$required_go" ]]; then
  echo "error: libtailscale requires go$required_go, found $actual_go" >&2
  exit 1
fi
if [[ -f "$out" && -f "$provenance" && "$out" -nt "$lock" && "$out" -nt "${BASH_SOURCE[0]}" ]]; then
  read -r recorded_android recorded_core recorded_sha <"$provenance"
  if [[ "$recorded_android" == "$android_commit" && "$recorded_core" == "$core_commit" &&
        "$recorded_sha" == "$(sha256sum "$out" | awk '{print $1}')" ]]; then
    echo "$out"
    exit 0
  fi
fi
rm -f "$out" "$out.tmp.aar" "$provenance"

mkdir -p "$build_root"
if [[ ! -d "$src/.git" ]]; then
  git clone --filter=blob:none --no-checkout "$android_repository" "$src"
fi
git -C "$src" fetch --depth=1 origin "$android_commit"
git -C "$src" checkout --detach --force "$android_commit"
[[ "$(git -C "$src" rev-parse HEAD)" == "$android_commit" ]]

# The selected Android commit is the first official Android baseline using Go
# 1.26.3 after core v1.98.2. Replace its next-development core pseudo-version
# with the immutable stable core requested by the project baseline.
(
  cd "$src"
  go mod edit -require="tailscale.com@$core_ref"
  go mod download "tailscale.com@$core_ref"
  resolved_core="$(go mod download -json "tailscale.com@$core_ref" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Dir"])')"
  [[ "$(git -C "$resolved_core" rev-parse HEAD 2>/dev/null || true)" == "$core_commit" ]] || {
    # Module cache directories do not necessarily retain .git; verify Go's sum
    # and the tag-to-commit mapping independently instead.
    remote_commit="$(git ls-remote https://github.com/tailscale/tailscale.git "refs/tags/$core_ref^{}" | awk '{print $1}')"
    [[ "$remote_commit" == "$core_commit" ]]
  }
  go mod tidy
  gobin="$build_root/bin"
  mkdir -p "$gobin"
  GOBIN="$gobin" go install golang.org/x/mobile/cmd/gomobile
  GOBIN="$gobin" go install golang.org/x/mobile/cmd/gobind
  export PATH="$gobin:$PATH"
  "$gobin/gomobile" bind \
    -target android/arm64 \
    -androidapi 26 \
    -ldflags "-linkmode=external -extldflags=-Wl,-z,max-page-size=16384" \
    -o "$out.tmp.aar" ./libtailscale
)
mv "$out.tmp.aar" "$out"
printf '%s %s %s\n' "$android_commit" "$core_commit" "$(sha256sum "$out" | awk '{print $1}')" >"$provenance.tmp"
mv "$provenance.tmp" "$provenance"
echo "$out"
