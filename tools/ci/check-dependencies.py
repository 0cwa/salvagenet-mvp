#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[2]
banned=('android.','androidx.','org.nodehost.qemu','org.nodehost.mesh','org.nodehost.store','org.nodehost.api','com.excp.podroid','io.ktor','androidx.room')
for module in ('node-model','node-core'):
    for p in (root/'android/modules'/module/'src/main').rglob('*.kt'):
        for line in p.read_text().splitlines():
            if line.startswith('import ') and any(x in line for x in banned): raise SystemExit(f'{p.relative_to(root)}: banned inward dependency: {line}')
print('onion dependency imports OK')
