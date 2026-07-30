# Linux host QEMU profile laboratory

This optional E3 laboratory boots the Ubuntu ARM64 UEFI profile with host QEMU, cloud-init, SLIRP, loopback SSH, and a real QMP monitor. It isolates profile/cloud-init failures from Android packaging failures.

```sh
make qemu-lab-e2e

# Individual debugging steps
make qemu-lab-prepare
make qemu-lab-start
make qemu-lab-smoke
make qemu-lab-stop
```

Artifacts, generated test keys, logs, and `evidence.json` stay under `.local/qemu-lab/`. A passing host-QEMU test does not prove the Android QEMU binary, foreground service, VpnService, OEM lifecycle behavior, or any physical acceptance gate.

H02 extends this baseline with disposable Headscale guest enrollment, restart/recovery, and secret-persistence inspection.
