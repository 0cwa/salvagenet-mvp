#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {
    "qemuExtraArgs",
    "kernelExtraCmdline",
    "rawQmp",
    "shellCommand",
    "arbitraryCommand",
}
PATHS = [
    ROOT / "control",
    ROOT / "android" / "modules" / "node-model" / "src" / "main",
    ROOT / "android" / "modules" / "node-core" / "src" / "main",
    ROOT / "android" / "modules" / "control-api" / "src" / "main",
]
for base in PATHS:
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        for forbidden in FORBIDDEN:
            if forbidden in text:
                raise SystemExit(
                    f"release/public surface contains forbidden field {forbidden}: "
                    f"{path.relative_to(ROOT)}"
                )
print("release/public surface contains no raw execution fields")
