#!/usr/bin/env python3
"""Validate the reviewed roadmap seed without network access or mutation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .common import SEED_PATH, load_json, validate_seed
except ImportError:  # direct script execution from Makefile/CI
    from common import SEED_PATH, load_json, validate_seed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    parser.add_argument("--no-active-task-check", action="store_true")
    args = parser.parse_args()
    seed = load_json(args.seed)
    facts = validate_seed(seed, check_active_tasks=not args.no_active_task_check)
    print(json.dumps({"valid": True, **facts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
