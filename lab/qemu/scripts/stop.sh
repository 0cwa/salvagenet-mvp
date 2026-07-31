#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"

cleanup=false
evidence_path=
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cleanup)
      cleanup=true
      shift
      ;;
    --evidence)
      [[ $# -ge 2 && -z $evidence_path ]] || { echo "invalid --evidence" >&2; exit 2; }
      evidence_path=$2
      shift 2
      ;;
    *)
      echo "usage: $0 [--cleanup --evidence PATH]" >&2
      exit 2
      ;;
  esac
done
if [[ $cleanup == true && -z $evidence_path ]]; then
  echo "--cleanup requires --evidence PATH" >&2
  exit 2
fi
if [[ $cleanup == false && -n $evidence_path ]]; then
  echo "--evidence requires --cleanup" >&2
  exit 2
fi

if [[ -e "$state/qemu.pid" ]]; then
  pid=$(read_qemu_pid) || {
    echo "invalid H02A QEMU pid file; refusing to signal any process" >&2
    exit 2
  }
  if kill -0 "$pid" 2>/dev/null; then
    qemu_pid_matches "$pid" || {
      echo "refusing to signal pid $pid: process identity differs from H02A QEMU" >&2
      exit 2
    }
    ssh_nodeadmin 15 'sudo systemctl poweroff' >/dev/null 2>&1 || true
    if ! wait_for_qemu_exit 150; then
      pid=$(live_qemu_pid) || {
        echo "H02A QEMU identity was lost while stopping" >&2
        exit 1
      }
      kill "$pid" 2>/dev/null || true
      if ! wait_for_qemu_exit 15; then
        pid=$(live_qemu_pid) || {
          echo "H02A QEMU identity was lost before forced stop" >&2
          exit 1
        }
        kill -KILL "$pid" 2>/dev/null || true
        wait_for_qemu_exit 15
      fi
    fi
  else
    rm -f "$state/qemu.pid" "$state/qmp.sock"
  fi
fi
rm -f "$state/qemu.pid" "$state/qmp.sock"
qemu_running && { echo "QEMU remains live after stop" >&2; exit 1; }

if [[ $cleanup == true ]]; then
  python3 - "$state" "$evidence_path" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import stat
import sys

state = Path(sys.argv[1]).resolve(strict=True)
raw_evidence = Path(sys.argv[2]).expanduser()
if not raw_evidence.is_absolute():
    raw_evidence = Path.cwd() / raw_evidence
if raw_evidence.is_symlink():
    raise SystemExit('evidence path must not be a symlink')
evidence = raw_evidence.resolve(strict=True)
evidence_root_path = state / 'evidence'
if evidence_root_path.is_symlink():
    raise SystemExit('retained evidence directory must not be a symlink')
evidence_root = evidence_root_path.resolve(strict=True)
try:
    evidence.relative_to(evidence_root)
except ValueError:
    raise SystemExit('evidence path is outside the retained evidence directory')
if evidence.name != 'evidence.json' or not evidence.is_file():
    raise SystemExit('evidence path is missing or unsafe')
base_name = 'ubuntu-24.04-server-cloudimg-arm64.img'
retained = sorted([base_name, 'evidence'])
removed: list[str] = []
budget = 4096


def delete(path: Path) -> None:
    global budget
    budget -= 1
    if budget < 0:
        raise SystemExit('cleanup exceeded the entry bound')
    metadata = path.lstat()
    if stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
        for child in sorted(path.iterdir(), key=lambda value: value.name):
            delete(child)
        path.rmdir()
    else:
        path.unlink()


for entry in sorted(state.iterdir(), key=lambda value: value.name):
    if entry.name in retained:
        continue
    removed.append(entry.name)
    delete(entry)
actual = sorted(path.name for path in state.iterdir())
if actual != retained:
    raise SystemExit(f'cleanup retained unexpected state: {actual}')
base = state / base_name
if base.is_symlink() or not base.is_file() or not evidence_root_path.is_dir():
    raise SystemExit('cleanup retained unsafe base or evidence state')
receipt = {
    'schemaVersion': 1,
    'qemuStopped': True,
    'retained': retained,
    'removed': removed,
}
path = evidence.parent / 'cleanup.json'
temporary = path.with_name(path.name + '.tmp')
if path.is_symlink() or path.parent.is_symlink() or temporary.is_symlink():
    raise SystemExit('cleanup receipt path is unsafe')
temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
temporary.chmod(0o600)
temporary.replace(path)
PY
fi
suffix=
if [[ $cleanup == true ]]; then
  suffix=' and cleaned'
fi
printf 'host-QEMU lab stopped%s\n' "$suffix"
