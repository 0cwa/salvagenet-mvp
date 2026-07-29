#!/usr/bin/env bash
set -euo pipefail
if command -v docker >/dev/null 2>&1 \
    && docker info >/dev/null 2>&1 \
    && docker compose version >/dev/null 2>&1; then
  echo docker-compose
elif command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
  if podman compose version >/dev/null 2>&1; then
    echo podman-compose
  else
    # Podman itself is sufficient for this single-container laboratory.
    echo podman-direct
  fi
else
  echo "no authorized docker/podman runtime" >&2
  exit 1
fi
