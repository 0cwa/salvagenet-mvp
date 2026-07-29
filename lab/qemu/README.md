# Linux host QEMU profile laboratory

This optional E3 laboratory boots the Ubuntu ARM64 UEFI profile with host QEMU,
cloud-init, SLIRP, and loopback SSH. It isolates profile/cloud-init failures from
Android packaging failures.

```sh
make qemu-lab-prepare   # downloads and verifies the current Ubuntu image
make qemu-lab-start
make qemu-lab-smoke
make qemu-lab-stop
```

Artifacts and the generated test key stay under `.local/qemu-lab/`. A passing
host-QEMU test does not prove the Android QEMU binary, foreground service,
VpnService, or OEM lifecycle behavior.
