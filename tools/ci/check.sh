#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
cd "$root"
python3 tools/ci/check-agents.py
python3 tools/ci/check-context-hygiene.py
python3 tools/ci/check-tasks.py
python3 tools/ci/check-references.py
python3 tools/ci/check-schemas.py
python3 tools/ci/check-evidence.py
python3 tools/ci/check-status.py
python3 tools/ci/check-profiles.py
python3 tools/ci/check-openapi.py
python3 tools/ci/check-dependencies.py
python3 tools/ci/check-release-surface.py
python3 tools/ci/check-secrets.py
python3 tools/ci/check-todos.py
python3 tools/profiles/validate.py
tools/ci/check-shell.sh
tools/ci/check-kotlin-pure.sh
tools/ci/check-python.sh
python3 tools/ci/check-mvp-plus-gate.py --report-only
for task in T00 T01 T02 T03 T04 T05 T06 T07 T08 T09; do python3 tools/agents/context-pack.py "$task" >/dev/null; done
echo 'repository validation: PASS'
