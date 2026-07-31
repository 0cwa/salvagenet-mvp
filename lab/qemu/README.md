# Linux host QEMU profile laboratory

This laboratory boots Ubuntu ARM64 under host QEMU with UEFI, NoCloud, SLIRP, loopback SSH, and a real QMP monitor. It isolates guest image and initialization failures from Android execution and packaging failures.

```sh
make qemu-lab-e2e

# Individual debugging steps
make qemu-lab-prepare
make qemu-lab-start
make qemu-lab-smoke   # records the initial stage
make qemu-lab-stop
```

## Canonical preparation contract

`make qemu-lab-prepare`:

- validates the exact checked-in `ubuntu-2404-arm64-uefi` profile;
- consumes the immutable 2026-07-25 Ubuntu ARM64 release lock without rewriting it;
- verifies the exact 618,098,176-byte image and SHA-256 before use;
- renders canonical Ubuntu vendor-data with the production renderer;
- adds only an ephemeral SSH public key, strict SSH policy, and mesh-independent readiness marker through test-only shell user-data;
- creates an independent copied-writable qcow2 system disk, not a backing-file overlay;
- creates the profile's persistent raw data disk;
- records AAVMF source paths, digests, sizes, package facts, tool facts, source commit, dirty state, and the closed QEMU command in `preflight.json` before launch.

`make qemu-lab-start` executes the recorded `qemu-command.json`. It verifies that the command still matches preflight and refuses stale PID files that point at an unrelated process.

## Runtime qualification contract

`make qemu-lab-e2e` performs three independently recorded stages:

1. initial canonical boot;
2. a clean guest reboot;
3. guest poweroff followed by a complete QEMU stop/start.

Every stage requires:

- a bounded QMP greeting/capability exchange and `query-status == running`;
- `cloud-init status --wait` completion and the test-only readiness marker;
- key-only loopback SSH;
- effective `sshd -T` policy disabling password, keyboard-interactive, and root login;
- failed password-only, keyboard-interactive-only, and root-key client attempts;
- a persisted SSH host-key fingerprint;
- guest cloud-init, OpenSSH, and kernel facts;
- bounded local seed and guest-state scans for bootstrap, callback, Headscale, and Tailscale material;
- serial, QEMU stdout, and QEMU stderr snapshots.

The final evidence assembler rejects inferred or partial results. It requires three distinct boot IDs, one stable SSH host key, all nine bounded log snapshots, exact preparation identities, and explicit `host-qemu` classification. Successful cleanup retains only:

- `ubuntu-24.04-server-cloudimg-arm64.img` as the verified immutable cache;
- the bounded `evidence/` directory containing `evidence.json` and `cleanup.json`.

A failed run stops the recognized QEMU process when possible but retains diagnostic state under `.local/qemu-lab/`. A successful run prints the exact evidence path. Implementation and tests alone are not a host qualification result; the real run and evidence must still be reviewed.

Normal preparation resets generated disks, firmware copies, keys, seed media, sockets, and logs. Updating the image lock is a separate reviewed action:

```sh
tools/profiles/pin-ubuntu-image.sh YYYYMMDD
```

Artifacts and generated state stay under `.local/qemu-lab/`. A passing host-QEMU test does not prove the Android QEMU binary, foreground service, VpnService, OEM lifecycle behavior, guest mesh, or any physical acceptance gate.

H02B is a separate later phase for guest Headscale/Tailscale identity and recovery. Do not add mesh behavior to H02A.
