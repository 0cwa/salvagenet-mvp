#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
python3 -m compileall -q "$root/tools" "$root/controller/mvp-cli" "$root/tests/tools" "$root/lab/headscale/tests"
PYTHONPATH="$root/controller/mvp-cli" python3 -m unittest discover -s "$root/controller/mvp-cli/tests"
python3 -m unittest discover -s "$root/tests/tools"
python3 -m unittest discover -s "$root/lab/headscale/tests"
echo 'python compile/tests OK'
