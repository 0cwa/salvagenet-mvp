#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd)); cd "$root"
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
python3 - <<'PY_INNER_CHECK'
import json, subprocess
from pathlib import Path
for item in json.loads(Path('agents/task-dag.json').read_text())['tasks']:
    subprocess.run(['python3','tools/agents/context-pack.py',item['id']],check=True,stdout=subprocess.DEVNULL)
PY_INNER_CHECK
echo 'repository validation: PASS'
