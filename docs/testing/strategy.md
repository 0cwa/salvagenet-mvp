# Testing strategy

## Environments

### E0 — static and contract tests

Python/schema/shell/task/context/provenance checks. Runs without Android SDK or Podroid.

### E1 — JVM/Android unit tests

Gradle unit tests for domain, reconciler, command compiler, profile parser, Room adapters, and API handlers. No physical device.

### E2 — Android emulator

Activity/service recreation, import UI, Room persistence, API lifecycle, and fake runtime/mesh. Use `lab/android-emulator/`; never use it to claim APK-native QEMU, Android VPN, thermal, or OEM behavior.

### E3 — Linux QEMU/profile lab

Use `lab/qemu/` to qualify Ubuntu/cloud-init/SSH independently of Android packaging. A pass here does not satisfy an APK-native QEMU gate.

### E4 — small physical HIL environment

Use `tests/hil/` with one configured ARM64 phone. The standard-library runner composes the real APK, Host API, controller CLI, Headscale lab, QEMU process, guest mesh, and SSH through three scenarios:

- `smoke`: APK-native QEMU and stop/restart;
- `mvp`: host mesh/API, Ubuntu, guest mesh, ordinary/recovery SSH;
- `resilience`: service/QEMU failure, controller-offline continuity, and optional reboot.

The persistent development mode preserves enrollment and VPN consent between `adb install -r` runs. Clean first-run enrollment and secure-lock cold boot remain explicit release checks until repeated use justifies UI automation.

## Orthogonal test boundaries

- scenarios express product behavior;
- adapters own ADB, Headscale, controller, SSH, and subprocess commands;
- evidence recording is independent of scenario decisions;
- product modules do not import HIL code;
- old device/E2E scripts delegate to the HIL runner.

## MVP rule

A hardware-dependent gate may be `BLOCKED-HARDWARE`, never inferred as passing from a fake, emulator, host-QEMU run, or code review. A physical pass must reference the HIL run directory, source commit, exact APK SHA-256, device facts, commands, and assertions.
