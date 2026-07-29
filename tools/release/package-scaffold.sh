#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:-"$root/../nodehost-mvp-scaffold.tar.gz"}
cd "$root"
make validate
# git archive is deterministic once the scaffold is committed; fall back to tar before init.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git rev-parse HEAD >/dev/null 2>&1; then
  git archive --format=tar.gz --prefix=nodehost-mvp-scaffold/ -o "$out" HEAD
else
  tar --exclude=.git --exclude=.local --exclude=.worktrees --exclude=.venv \
      --exclude='lab/headscale/data' --exclude='lab/headscale/secrets' \
      -czf "$out" -C "$root/.." "$(basename "$root")"
fi
printf 'created %s\n' "$out"
