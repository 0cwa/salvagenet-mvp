#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$root"
python3 -m venv .venv 2>/dev/null || true
if [[ -x .venv/bin/pip && -s requirements-dev.txt ]]; then .venv/bin/pip install --disable-pip-version-check -r requirements-dev.txt; fi
tools/provenance/install-hooks.sh 2>/dev/null || true
tools/ci/check.sh
