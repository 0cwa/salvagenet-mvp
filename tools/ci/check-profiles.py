#!/usr/bin/env python3
from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
profiles={}
for p in root.glob('profiles/*/profile.json'):
    d=json.loads(p.read_text()); pid=d['metadata']['id']; assert p.parent.name==pid; profiles[pid]=d
required={'alpine-direct-qualification','ubuntu-2404-arm64-uefi','k3s-worker-lab'}
assert required<=profiles.keys()
assert profiles['alpine-direct-qualification']['spec']['boot']['type']=='direct-kernel'
assert profiles['ubuntu-2404-arm64-uefi']['spec']['boot']['type']=='uefi'
k=profiles['k3s-worker-lab']; assert k['metadata']['extends']=='ubuntu-2404-arm64-uefi'; assert 'cgroup-v2' in k['spec']['requirements']['qualificationChecks']
for pid,d in profiles.items():
    text=json.dumps(d).lower()
    for field in ('qemuargs','kernelextra','shellcommand','rawqmp'): assert field not in text, f'{pid}: forbidden {field}'
print('profile registry OK:',', '.join(sorted(profiles)))
