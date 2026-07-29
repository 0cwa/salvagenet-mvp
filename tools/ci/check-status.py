#!/usr/bin/env python3
"""Fail when generated MVP status has drifted from the evidence ledger."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "tools/status/generate.py"
spec = importlib.util.spec_from_file_location("nodehost_status", GENERATOR)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load status generator")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

failures: list[str] = []
for path, expected in module.generated_outputs(ROOT).items():
    actual = path.read_text(encoding="utf-8") if path.exists() else ""
    if actual.rstrip() != expected.rstrip():
        failures.append(str(path.relative_to(ROOT)))
if failures:
    raise SystemExit("generated status is stale: " + ", ".join(failures) + "; run `make mvp-status`")
print("MVP status documents: current")
