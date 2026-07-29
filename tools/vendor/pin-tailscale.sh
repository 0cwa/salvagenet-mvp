#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 2 ]] || { echo "usage: $0 <ref> <commit>" >&2; exit 2; }
ref=$1
commit=$2
[[ $commit =~ ^[0-9a-f]{40}$ ]] || { echo "commit must be a full 40-character SHA" >&2; exit 2; }

python3 - "$ref" "$commit" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys

path = Path("android/vendor/tailscale/tailscale.lock")
data = json.loads(path.read_text(encoding="utf-8"))
data["ref"] = sys.argv[1]
data["commit"] = sys.argv[2]
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

printf 'pinned tailscale ref %s at %s\n' "$ref" "$commit"
