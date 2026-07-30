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

The current baseline is useful but not yet H02A-qualified: preparation still writes parallel cloud-init data, advances Ubuntu `current` during a run, and does not bind selected firmware identities into evidence.

H02A upgrades the flow to:

- consume the canonical Ubuntu profile and rendered vendor-data;
- use a clearly test-only user-data layer for the ephemeral SSH key and readiness marker;
- consume a reviewed pinned Ubuntu lock;
- record selected AAVMF paths, digests, sizes, and host facts;
- prove QMP, cloud-init, key-only SSH, guest reboot, and complete QEMU restart;
- scan bounded state for forbidden bootstrap/mesh material;
- clean up generated state while retaining documented evidence and the cached pinned image.

Artifacts, generated test keys, overlays, firmware copies, sockets, logs, and `evidence.json` stay under `.local/qemu-lab/`. A passing host-QEMU test does not prove the Android QEMU binary, foreground service, VpnService, OEM lifecycle behavior, guest mesh, or any physical acceptance gate.

H02B is a separate later phase for guest Headscale/Tailscale identity and recovery. Do not add mesh behavior to H02A.
