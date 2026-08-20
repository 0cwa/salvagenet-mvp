#!/usr/bin/env python3
"""Repository-aware CLI for Podroid's pinned runtime preparation."""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION = Path(__file__).with_name("podroid_runtime.py")


def load_implementation() -> ModuleType:
    spec = importlib.util.spec_from_file_location("salvagenet_podroid_runtime", IMPLEMENTATION)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Podroid runtime implementation: {IMPLEMENTATION}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # The implementation originated inside the imported Podroid tree. Keep its
    # artifact logic intact while making repository-owned paths explicit here.
    module.LOCK_PATH = ROOT / "android" / "upstream" / "podroid-runtime.lock"
    module.SOURCE_ASSETS = ROOT / "android" / "podroid" / "app" / "src" / "main" / "assets"
    return module


def main() -> int:
    module = load_implementation()
    try:
        return module.main()
    except (OSError, module.RuntimeErrorWithContext, zipfile.BadZipFile) as error:
        print(f"Podroid runtime preparation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
