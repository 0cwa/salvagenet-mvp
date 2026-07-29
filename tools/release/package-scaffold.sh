#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
source_archive=${1:-"$root/../nodehost-mvp-scaffold.tar.gz"}
base=${source_archive%.tar.gz}
bundle="${base}.git.bundle"
checksums="${base}.SHA256SUMS"
cd "$root"

make validate
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1 || ! git rev-parse HEAD >/dev/null 2>&1; then
  echo 'package requires the committed Git scaffold so source and provenance agree' >&2
  exit 2
fi
if [[ -n $(git status --porcelain --untracked-files=normal) ]]; then
  echo 'working tree must be clean before packaging' >&2
  git status --short >&2
  exit 2
fi

rm -f "$source_archive" "$bundle" "$checksums"
git archive --format=tar.gz --prefix=nodehost-mvp-scaffold/ -o "$source_archive" HEAD
git bundle create "$bundle" main
(
  cd "$(dirname "$source_archive")"
  sha256sum "$(basename "$source_archive")" "$(basename "$bundle")" > "$(basename "$checksums")"
)
printf 'created %s\ncreated %s\ncreated %s\n' "$source_archive" "$bundle" "$checksums"
