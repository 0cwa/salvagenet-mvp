#!/usr/bin/env python3
from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
d=json.loads((root/'control/openapi.yaml').read_text()); assert d['openapi'].startswith('3.1')
paths=d['paths']; required={'/v1/status','/v1/profiles','/v1/images','/v1/image-imports','/v1/vms','/v1/vms/{id}','/v1/operations','/v1/operations/{id}','/v1/diagnostics','/v1/vms/{id}/ssh'}
assert required<=paths.keys()
text=json.dumps(d).lower()
for forbidden in ('shellcommand','qemuargs','kernelargs','rawqmp'): assert forbidden not in text
print(f'OpenAPI surface OK ({len(paths)} paths)')
