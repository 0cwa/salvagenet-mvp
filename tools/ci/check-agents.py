#!/usr/bin/env python3
from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
required=[root/'AGENTS.md',root/'docs/AGENTS.md',root/'android/AGENTS.md',root/'profiles/AGENTS.md',root/'tests/AGENTS.md']
required += [p/'AGENTS.md' for p in (root/'android/modules').iterdir() if p.is_dir()]
for task in json.loads((root/'agents/task-registry.json').read_text())['tasks']:
    d=root/'agents/tasks'/task['id']; required += [d/'task.md',d/'context.list',d/'allowed-paths.txt']
missing=[p.relative_to(root).as_posix() for p in required if not p.exists()]
assert not missing, 'missing scoped instruction/packet files: '+', '.join(missing)
print(f'AGENTS/task packet coverage OK ({len(required)} required files)')
