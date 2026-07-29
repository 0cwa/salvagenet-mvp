#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel 2>/dev/null || cd "$(dirname "$0")/../.." && pwd)
url=${UBUNTU_IMAGE_URL:-https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-arm64.img}
sums=${UBUNTU_SUMS_URL:-https://cloud-images.ubuntu.com/noble/current/SHA256SUMS}
out=${1:-$root/.local/artifacts/noble-server-cloudimg-arm64.img}
mkdir -p "$(dirname "$out")"

curl --fail --location --continue-at - --output "$out" "$url"
expected=$(curl --fail --location --silent "$sums" | awk '
  $2=="*noble-server-cloudimg-arm64.img" || $2=="noble-server-cloudimg-arm64.img" {print $1; exit}
')
actual=$(sha256sum "$out" | awk '{print $1}')
[[ -n "$expected" && "$actual" == "$expected" ]] || {
  echo "Ubuntu image digest mismatch" >&2
  exit 1
}

python3 - "$root" "$actual" "$(stat -c %s "$out")" "$url" <<'PY'
from __future__ import annotations

import datetime
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
digest = sys.argv[2]
size = int(sys.argv[3])
url = sys.argv[4]
path = root / "profiles/locks/images.lock.json"
data = json.loads(path.read_text(encoding="utf-8"))
artifact = data["artifacts"]["ubuntu-2404-arm64-cloud"]
artifact["source"] = {"kind": "remote", "url": url}
artifact["sha256"] = digest
artifact["sizeBytes"] = size
data["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

printf 'pinned %s (%s bytes)\n' "$actual" "$(stat -c %s "$out")"
