#!/usr/bin/env python3
"""Keep root-level implementation directories intentional and agent-readable."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_ROOT_DIRECTORIES = {
    "android",
    "agents",
    "control",
    "controller",
    "docs",
    "evidence",
    "lab",
    "profiles",
    "provenance",
    "tests",
    "tools",
}


def contains_files(path: Path) -> bool:
    """Ignore empty checkout artifacts while still rejecting tracked placeholder content."""
    return any(candidate.is_file() or candidate.is_symlink() for candidate in path.rglob("*"))


actual = {
    path.name
    for path in ROOT.iterdir()
    if path.is_dir() and not path.name.startswith(".") and contains_files(path)
}
unexpected = sorted(actual - ALLOWED_ROOT_DIRECTORIES)
missing = sorted(ALLOWED_ROOT_DIRECTORIES - actual)
assert not unexpected, (
    "unexpected root directories; add executable work under an owning root or update the "
    f"reviewed allowlist in the same active task: {unexpected}"
)
assert not missing, f"required repository roots are missing: {missing}"
for placeholder in ("hostd", "usb-link"):
    root = ROOT / placeholder
    assert not root.exists() or not contains_files(root), (
        f"deferred placeholder root reintroduced: {placeholder}; keep the design under docs/ until activation"
    )
print("root directory boundary OK")
