#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))
release=${1:-}
out=${2:-$root/.local/artifacts/ubuntu-24.04-server-cloudimg-arm64.img}
if [[ ! $release =~ ^20[0-9]{6}$ ]]; then
  echo "usage: $0 YYYYMMDD [output-image]" >&2
  echo "an explicit immutable Ubuntu release date is required" >&2
  exit 2
fi
base="https://cloud-images.ubuntu.com/releases/noble/release-$release"
image=ubuntu-24.04-server-cloudimg-arm64.img
url="$base/$image"
sums="$base/SHA256SUMS"
mkdir -p "$(dirname "$out")"

headers=$(curl --fail --silent --show-error --location --head \
  --proto '=https' --tlsv1.2 --connect-timeout 30 --max-time 120 "$url")
size=$(printf '%s\n' "$headers" | awk 'BEGIN{IGNORECASE=1} /^content-length:/ {gsub("\r",""); value=$2} END{print value}')
[[ $size =~ ^[1-9][0-9]*$ ]] || { echo "Ubuntu release did not provide an exact Content-Length" >&2; exit 1; }
expected=$(curl --fail --silent --show-error --location \
  --proto '=https' --tlsv1.2 --connect-timeout 30 --max-time 120 "$sums" |
  awk -v name="$image" '$2 == "*" name || $2 == name {print $1; exit}')
[[ $expected =~ ^[0-9a-f]{64}$ ]] || { echo "Ubuntu release SHA256SUMS has no exact ARM64 image entry" >&2; exit 1; }

valid_existing=false
if [[ -f $out && $(stat -c %s "$out") == "$size" ]]; then
  actual=$(sha256sum "$out" | awk '{print $1}')
  [[ $actual == "$expected" ]] && valid_existing=true
fi
if [[ $valid_existing != true ]]; then
  temporary="$out.part"
  curl --fail --location --proto '=https' --tlsv1.2 \
    --connect-timeout 30 --max-time 3600 --retry 2 --continue-at - \
    --output "$temporary" "$url"
  [[ $(stat -c %s "$temporary") == "$size" ]] || { echo "Ubuntu image size mismatch" >&2; exit 1; }
  actual=$(sha256sum "$temporary" | awk '{print $1}')
  [[ $actual == "$expected" ]] || { echo "Ubuntu image digest mismatch" >&2; exit 1; }
  mv -f "$temporary" "$out"
fi

python3 - "$root" "$release" "$expected" "$size" "$url" <<'PY'
from __future__ import annotations

import datetime
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
release = sys.argv[2]
digest = sys.argv[3]
size = int(sys.argv[4])
url = sys.argv[5]
path = root / "profiles/locks/images.lock.json"
data = json.loads(path.read_text(encoding="utf-8"))
artifact = data["artifacts"]["ubuntu-2404-arm64-cloud"]
artifact["source"] = {"kind": "remote-release", "release": release, "url": url}
artifact["sha256"] = digest
artifact["sizeBytes"] = size
data["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

printf 'pinned immutable Ubuntu release %s: %s (%s bytes)\n' "$release" "$expected" "$size"
