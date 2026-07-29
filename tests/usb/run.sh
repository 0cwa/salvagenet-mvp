#!/usr/bin/env bash
set -euo pipefail
python3 tools/ci/check-mvp-plus-gate.py
printf 'MVP+ gate passed; T09 must replace this scaffold with AOA/stream/TAP tests.
'
exit 77
