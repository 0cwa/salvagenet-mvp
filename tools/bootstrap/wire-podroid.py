#!/usr/bin/env python3
"""Compatibility wrapper for the Podroid patch-series workflow."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "tools" / "vendor" / "podroid.py"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    command = "verify" if args.check else "apply-patches"
    argv = ["python3", str(VENDOR), command]
    if args.check:
        argv.append("--offline")
    return subprocess.call(argv, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
