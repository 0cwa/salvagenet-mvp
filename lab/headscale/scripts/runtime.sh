#!/usr/bin/env bash
set -euo pipefail
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo docker
elif command -v podman >/dev/null 2>&1; then
  echo podman
else
  echo "no authorized docker/podman runtime" >&2; exit 1
fi
