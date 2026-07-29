# API 36 Android emulator laboratory

The emulator is optional and deliberately separate from the physical-device
QEMU gate. It is useful for Compose/import flows, service recreation, Room,
Host API lifecycle, and fake runtime/mesh tests.

```sh
make emulator-install
make emulator-start
adb wait-for-device
# Run instrumented/fake-adapter tests.
make emulator-stop
```

The installer selects an x86_64 system image on x86_64 hosts and an arm64 image
on arm64 hosts. Hardware acceleration requires current-user access to `/dev/kvm`
when available.
