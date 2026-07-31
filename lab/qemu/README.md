# Linux host QEMU profile laboratory

This laboratory boots Ubuntu ARM64 under host QEMU with UEFI, NoCloud, SLIRP, loopback SSH, and a real QMP monitor. It isolates guest image and initialization failures from Android execution and packaging failures.

```sh
make qemu-lab-e2e

# Individual debugging steps
make qemu-lab-prepare
make qemu-lab-start
make qemu-lab-smoke
make qemu-lab-stop
```

## Canonical preparation contract

`make qemu-lab-prepare` now:

- validates the exact checked-in `ubuntu-2404-arm64-uefi` profile;
- consumes the immutable 2026-07-25 Ubuntu ARM64 release lock without rewriting it;
- verifies the exact 618,098,176-byte image and SHA-256 before use;
- renders canonical Ubuntu vendor-data with the production renderer;
- adds only an ephemeral SSH public key, strict SSH policy, and mesh-independent readiness marker through test-only user-data;
- creates an independent copied-writable qcow2 system disk, not a backing-file overlay;
- creates the profile's persistent raw data disk;
- records AAVMF source paths, digests, sizes, package facts, tool facts, source commit, dirty state, and the closed QEMU command in `preflight.json` before launch.

`make qemu-lab-start` executes the recorded `qemu-command.json`; it no longer carries a second hard-coded QEMU profile in shell.

The remaining H02A runtime qualification still must prove and record:

- real QMP `running` status and cloud-init completion;
- key-only loopback SSH plus negative password, keyboard-interactive, and root-login checks;
- a clean guest reboot and a complete QEMU stop/start;
- bounded forbidden-material scanning;
- exact cleanup and final machine-readable `host-qemu` evidence.

Normal runs keep the immutable base image as a cache but reset generated disks, firmware copies, keys, seed media, sockets, and logs. Updating the image lock is a separate reviewed action:

```sh
tools/profiles/pin-ubuntu-image.sh YYYYMMDD
```

Artifacts and generated state stay under `.local/qemu-lab/`. A passing host-QEMU test does not prove the Android QEMU binary, foreground service, VpnService, OEM lifecycle behavior, guest mesh, or any physical acceptance gate.

H02B is a separate later phase for guest Headscale/Tailscale identity and recovery. Do not add mesh behavior to H02A.
