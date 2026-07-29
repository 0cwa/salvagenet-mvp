#!/usr/bin/env python3
from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
profiles=[]
for path in sorted(root.glob('profiles/*/profile.json')):
    data=json.loads(path.read_text()); profiles.append(data['metadata']['id'])
    assert data['apiVersion']=='nodehost.example/v1alpha1'
    assert data['kind']=='VirtualMachineProfile'
    text=path.read_text().lower()
    for forbidden in ('qemuargs','kernelargs','shellcommand','rawqmp'):
        assert forbidden not in text, f'{path}: forbidden field {forbidden}'
required={'alpine-direct-qualification','ubuntu-2404-arm64-uefi','k3s-worker-lab'}
assert required <= set(profiles), f'missing profiles: {required-set(profiles)}'
print(f'profiles OK: {", ".join(profiles)}')
