#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"
for file in system.qcow2 seed.img AAVMF_CODE.fd AAVMF_VARS.fd; do
  [[ -f "$state/$file" ]] || { echo "missing $state/$file; run make qemu-lab-prepare" >&2; exit 2; }
done
if [[ -f "$state/qemu.pid" ]] && kill -0 "$(cat "$state/qemu.pid")" 2>/dev/null; then
  echo "host-QEMU lab already running"
  exit 0
fi

nohup qemu-system-aarch64 \
  -M virt,gic-version=3 \
  -cpu max \
  -accel tcg,thread=multi \
  -smp 2 -m 2048 \
  -display none -monitor none \
  -serial "file:$state/serial.log" \
  -drive "if=pflash,format=raw,readonly=on,file=$state/AAVMF_CODE.fd" \
  -drive "if=pflash,format=raw,file=$state/AAVMF_VARS.fd" \
  -drive "if=none,id=system,format=qcow2,file=$state/system.qcow2" \
  -device virtio-blk-pci,drive=system \
  -drive "if=none,id=seed,format=raw,readonly=on,file=$state/seed.img" \
  -device virtio-blk-pci,drive=seed \
  -netdev "user,id=net0,hostfwd=tcp:127.0.0.1:$ssh_port-:22" \
  -device virtio-net-pci,netdev=net0,romfile= \
  -qmp "unix:$state/qmp.sock,server=on,wait=off" \
  >"$state/qemu.stdout.log" 2>"$state/qemu.stderr.log" &
echo $! > "$state/qemu.pid"
printf 'started host-QEMU lab pid=%s ssh=127.0.0.1:%s\n' "$(cat "$state/qemu.pid")" "$ssh_port"
