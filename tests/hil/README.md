# Small hardware-in-the-loop runner

This directory is the single physical-device test path for the base MVP. It deliberately uses one Linux workstation, one dedicated ARM64 Android phone, the existing Headscale lab, the real `phonectl-mvp` client, and a standard-library Python runner.

```text
scenario
   +-- DevicePort ------ AdbDevice
   +-- ControllerPort -- phonectl-mvp / OpenSSH
   +-- MeshLabPort ----- existing Headscale container scripts
   +-- EvidenceRecorder
```

Scenarios contain product behavior and assertions. Adapters contain environment commands. The Android application contains no HIL-specific product logic.

## One-time setup

```sh
cp tests/hil/config.example.json .local/hil.json
# Edit the device serial, node names, guest SSH target, and image-import files.
make lab-up
make lab-keys
make hil-doctor
```

The phone must already have accepted the ADB RSA prompt. Persistent development mode assumes enrollment and Android VPN consent were completed once. Clean first-run enrollment remains a separate release/onboarding check.

## Scenarios

```sh
make hil-smoke       # APK install -> Alpine QEMU -> one process -> stop/restart
make hil-mvp         # host mesh/API -> Ubuntu -> guest mesh -> SSH/recovery
make hil-resilience  # service restart -> QEMU crash -> controller-silent smoke -> optional reboot
make hil-all
```

Set `HIL_BUILD=1` to build before a scenario. `hil-resilience` establishes a smoke baseline when no QEMU process is running. Reboot is opt-in through `resilience.allowReboot`.

The controller-silent assertion proves only that no request lease is required during the configured interval. It does not by itself close B17; H04 hardens actual controller/network-unavailable evidence separately.

## Evidence

Each run creates an ignored directory under `.local/hil-runs/` containing `run.json`, device facts, command records, optional Headscale snapshots, and failure-only bounded logcat. A `PASS` is bound to one source commit, one APK digest, one configured device, and the scenario assertions. Review local evidence before promoting it through the existing evidence tooling.

## Exit codes

- `0`: scenario passed.
- `1`: product assertion or exercised operation failed.
- `77`: required hardware/setup is absent or unauthorized.

Compatibility wrappers in `tests/e2e/` and `tests/device/` delegate here so the repository has only one physical-test implementation.
