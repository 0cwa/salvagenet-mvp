#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "evidence/schema/gate-evidence.schema.json").read_text())
seen: set[str] = set()
for path in sorted((ROOT / "evidence/gates").glob("*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(data)
    assert data["gateId"] == path.stem, f"{path}: gateId/file mismatch"
    assert data["gateId"] not in seen, f"duplicate evidence for {data['gateId']}"
    seen.add(data["gateId"])
print(f"acceptance evidence schema OK ({len(seen)} records)")
