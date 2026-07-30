# Small hardware-in-the-loop runner

This is the single physical-device path for the base MVP: one Linux workstation, one explicitly selected ARM64 Android phone, the existing Headscale lab, the real controller CLI, and standard-library Python.

## Setup and transport

```sh
cp tests/hil/config.example.json .local/hil.json
make lab-up
make lab-keys
make hil-doctor
```

`device.serial` is mandatory. `device.adbCommand` defaults to `["adb"]` and may point at a remote-device/streaming wrapper, but the runner still passes the exact serial and never chooses the first device. Live credentials stay in ignored files.

## Scenarios

```sh
make hil-smoke HIL_BUILD=1
make hil-mvp
make hil-resilience
make hil-all
```

SSH known-host state is isolated inside each run directory. Headscale identity assertions match exact node labels or their FQDN form, not arbitrary substrings.

`hil-resilience` has two distinct modes:

- with no isolation commands, it records a controller-silent smoke interval and leaves the actual-unavailability assertion skipped;
- with both `resilience.controllerOfflineCommand` and `controllerOnlineCommand`, it verifies the Host API becomes unavailable, the VM continues, then restores the controller path. Use disposable, narrowly scoped host commands and verify their cleanup.

## Evidence and promotion

Each run creates `.local/hil-runs/<run-id>/` with a compact run record, hashed device serial, per-run SSH trust, bounded redacted commands, device facts, and failure-only logcat. Recorded ADB argv redact the configured serial.

Promotion is dry-run by default:

```sh
python3 tools/evidence/promote-hil.py \
  --run-dir .local/hil-runs/<run-id> \
  --gate B02 \
  --summary 'APK-native Alpine/QEMU smoke passed'

# After reviewing every artifact:
python3 tools/evidence/promote-hil.py ... --write
```

The promotion tool requires the current commit, a valid APK digest, a PASS run, and gate-specific non-skipped assertions. B11 is intentionally not auto-promoted because key-only SSH configuration needs additional direct evidence.

## Exit codes

- `0`: scenario passed.
- `1`: product assertion or exercised operation failed.
- `77`: required hardware/setup is absent or unauthorized.

Compatibility wrappers under `tests/device/` and `tests/e2e/` delegate here. Fake, emulator, and host-QEMU results cannot close physical gates.
