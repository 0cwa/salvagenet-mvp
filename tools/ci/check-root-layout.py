#!/usr/bin/env python3
"""Keep tracked root-level implementation directories intentional and agent-readable."""
from __future__ import annotations

from pathlib import Path
import subprocess

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

tracked = subprocess.run(
    ["git", "ls-files", "-z"],
    cwd=ROOT,
    check=True,
    capture_output=True,
).stdout.decode("utf-8").split("\0")
actual = {
    path.split("/", 1)[0]
    for path in tracked
    if path and "/" in path and not path.startswith(".")
}
unexpected = sorted(actual - ALLOWED_ROOT_DIRECTORIES)
missing = sorted(ALLOWED_ROOT_DIRECTORIES - actual)
assert not unexpected, (
    "unexpected tracked root directories; add executable work under an owning root or update the "
    f"reviewed allowlist in the same active task: {unexpected}"
)
assert not missing, f"required tracked repository roots are missing: {missing}"
for placeholder in ("hostd", "usb-link"):
    assert placeholder not in actual, (
        f"deferred placeholder root reintroduced: {placeholder}; keep the design under docs/ until activation"
    )
print("tracked root directory boundary OK")
