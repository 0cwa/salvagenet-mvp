# Testing strategy

## Environments

### E0 — scaffold-only

Python/schema/shell/task/context/provenance checks. Runs without Android SDK or Podroid.

### E1 — imported JVM/Android unit tests

Gradle unit tests for domain, reconciler, command compiler, profile parser, Room adapters, and API handlers. No physical device.

### E2 — Android emulator

Activity/service recreation, import UI, Room persistence, API lifecycle, and fake runtime/mesh. Use `lab/android-emulator/`; never use it to claim QEMU-native performance, Android VPN reliability, or OEM compatibility.

### E3 — Linux QEMU/profile lab

Use `lab/qemu/` to boot the Ubuntu ARM64 UEFI profile under host QEMU and validate cloud-init plus key-only SSH independently of Android packaging. Extend the same lab for guest Tailscale and K3s qualification. A pass here does not satisfy APK-native QEMU gates.

### E4 — physical Android

APK-native QEMU execution, foreground-service lifecycle, VPN permission, embedded libtailscale, native page size, thermal/resource behavior, and network transitions.

### E5 — full Headscale end-to-end

Controller -> host mesh -> Host API -> QEMU guest -> guest mesh -> SSH/Ansible.

## Test layers

- pure state-machine and planner tests;
- adapter contract tests using fakes;
- QEMU argv golden/invariant tests;
- schema and profile validation;
- Room crash/recovery tests;
- Host API contract tests against OpenAPI examples;
- Headscale lab integration tests;
- physical-device lifecycle scripts;
- failure injection and soak tests.

## MVP rule

A hardware-dependent gate may be `BLOCKED-HARDWARE`, never silently converted to passing. The acceptance ledger distinguishes automated, manual, and deferred evidence.
