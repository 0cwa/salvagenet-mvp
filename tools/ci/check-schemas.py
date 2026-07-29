#!/usr/bin/env python3
from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
for path in [
    root/'control/schemas/node-enrollment.schema.json',
    root/'control/schemas/guest-bootstrap-secret.schema.json',
    root/'profiles/schema/vm-profile.schema.json',
]:
    data=json.loads(path.read_text()); assert data.get('$schema'); assert data.get('additionalProperties') is False
example=json.loads((root/'control/examples/node-enrollment.example.json').read_text())
assert example['apiVersion']=='nodehost.example/v1alpha1'; assert example['kind']=='NodeEnrollment'
guest_example=json.loads((root/'control/examples/guest-bootstrap-secret.example.json').read_text())
assert guest_example['kind']=='GuestBootstrapSecret'
# Use jsonschema when installed, retain structural checks without it.
try:
    import jsonschema
except ImportError:
    jsonschema=None
if jsonschema:
    jsonschema.Draft202012Validator(json.loads((root/'control/schemas/node-enrollment.schema.json').read_text()),format_checker=jsonschema.FormatChecker()).validate(example)
    jsonschema.Draft202012Validator(json.loads((root/'control/schemas/guest-bootstrap-secret.schema.json').read_text()),format_checker=jsonschema.FormatChecker()).validate(guest_example)
    ps=json.loads((root/'profiles/schema/vm-profile.schema.json').read_text())
    for profile in root.glob('profiles/*/profile.json'): jsonschema.Draft202012Validator(ps).validate(json.loads(profile.read_text()))
print('schemas/examples OK'+(' (jsonschema)' if jsonschema else ' (structural fallback)'))
