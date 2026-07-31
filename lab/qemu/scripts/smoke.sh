#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=lab/qemu/scripts/common.sh
source "$(dirname "$0")/common.sh"

stage=${1:-}
[[ $stage =~ ^(initial|guest-reboot|qemu-restart)$ ]] || {
  echo "usage: $0 initial|guest-reboot|qemu-restart" >&2
  exit 2
}
for file in id_ed25519 preflight.json qemu-command.json; do
  [[ -f "$state/$file" && ! -L "$state/$file" ]] || {
    echo "missing or unsafe $state/$file" >&2
    exit 2
  }
done
qemu_running || { echo "QEMU is not running" >&2; exit 1; }

python3 "$root/lab/qemu/scripts/h02a-qmp.py" \
  --socket "$state/qmp.sock" \
  --wait 300 \
  --output "$state/qmp-$stage.json"
wait_for_ssh 360

ssh_nodeadmin 360 'sudo cloud-init status --wait --long' > "$state/cloud-init-$stage.txt"
ssh_nodeadmin 30 'sudo cat /var/lib/nodehost/h02a-ready' > "$state/readiness-$stage.txt"
ssh_nodeadmin 30 'cat /proc/sys/kernel/random/boot_id' > "$state/boot-id-$stage.txt"
ssh_nodeadmin 30 \
  "sudo sshd -T | awk '\$1 == \"passwordauthentication\" || \$1 == \"kbdinteractiveauthentication\" || \$1 == \"permitrootlogin\" {print \$1, \$2}'" \
  > "$state/sshd-$stage.txt"

if ssh_root 12 true >/dev/null 2>&1; then
  echo "root key login unexpectedly succeeded" >&2
  exit 1
fi
ssh-keygen -lf "$known_hosts" -E sha256 | head -n 1 > "$state/host-key-$stage.txt"

python3 - "$state/sshd-$stage.txt" "$state/ssh-auth-$stage.json" <<'PY'
from pathlib import Path
import json
import sys
policy = {
    line.strip().lower()
    for line in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines()
    if line.strip()
}
expected = {
    'passwordauthentication no',
    'kbdinteractiveauthentication no',
    'permitrootlogin no',
}
if policy != expected:
    raise SystemExit(f'effective sshd policy differs from H02A contract: {sorted(policy)}')
result = {
    'keyOnlyLoopbackSsh': True,
    'rootKeyLoginRejected': True,
    'passwordAuthenticationDisabled': True,
    'keyboardInteractiveDisabled': True,
    'rootLoginDisabled': True,
}
path = Path(sys.argv[2])
temporary = path.with_name(path.name + '.tmp')
temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
temporary.chmod(0o600)
temporary.replace(path)
PY

remote_scan="$state/remote-secret-scan-$stage.json"
timeout 120 ssh "${ssh_options[@]}" nodeadmin@127.0.0.1 'sudo python3 - remote' \
  < "$root/lab/qemu/scripts/h02a-scan.py" \
  > "$remote_scan"
python3 "$root/lab/qemu/scripts/h02a-scan.py" combine \
  --state "$state" \
  --stage "$stage" \
  --remote "$remote_scan"
rm -f "$remote_scan"

for file in \
  "$state/cloud-init-$stage.txt" \
  "$state/readiness-$stage.txt" \
  "$state/boot-id-$stage.txt" \
  "$state/sshd-$stage.txt" \
  "$state/host-key-$stage.txt"; do
  chmod 0600 "$file"
done
snapshot_qemu_logs "$stage"
printf 'H02A stage %s: QMP running, cloud-init done, key-only SSH, scan clean\n' "$stage"
