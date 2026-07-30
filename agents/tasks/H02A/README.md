# H02A — Canonical Ubuntu guest boot qualification

Status: **PLANNED** and the sole active task in phase `guest-boot-1` after the transition PR merges.

```sh
make context TASK=H02A
```

H02A replaces the current handwritten host-QEMU cloud-init path with a flow bound to the canonical profile, rendered vendor-data, pinned Ubuntu image, and recorded AAVMF identities. A test-only user-data layer supplies the ephemeral SSH key without creating guest bootstrap or mesh secrets.

It proves UEFI/QMP, NoCloud, key-only loopback SSH, guest reboot, full QEMU stop/start, bounded forbidden-material scanning, cleanup, and host-QEMU evidence. It does not redeem one-use guest material, run Headscale/Tailscale, or close Android acceptance gates.
