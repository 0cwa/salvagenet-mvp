#!/usr/bin/env python3
import json
from pathlib import Path
root = Path(__file__).resolve().parents[2]
data = json.loads((root / 'agents/task-dag.json').read_text())
for wave in sorted({task['parallelGroup'] for task in data['tasks']}):
    names = ', '.join(f"{task['id']} ({task['slug']})" for task in data['tasks'] if task['parallelGroup'] == wave)
    print(f'wave {wave}: {names}')
