#!/usr/bin/env bash
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
git config core.hooksPath "$repo/.githooks"
echo "installed hooks from $repo/.githooks"
