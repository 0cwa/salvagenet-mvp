# H02 — Canonical Ubuntu guest boot qualification

Status: **PLANNED** and the sole active task in phase `guest-boot-1`.

Generate scoped context with:

```sh
make context TASK=H02
```

H02 proves the canonical Ubuntu/UEFI/NoCloud/key-only loopback SSH path in the existing host-QEMU lab. It does not add Headscale, guest-tailnet, emulator, Android-device, or compatibility-migration scope.

The lab is disposable alpha state: recreate it from canonical inputs rather than carrying obsolete images, profiles, or bootstrap formats forward.
