# Small hardware-in-the-loop runner

This is the single physical-device path for the base MVP: one Linux workstation, one explicitly selected ARM64 Android phone, the existing Headscale lab, the real controller CLI, and standard-library Python.

## Setup and transport

```sh
cp tests/hil/config.example.json .local/hil.json
make lab-up
make lab-keys
make hil-doctor
```

`device.serial` is mandatory. `device.adbCommand` defaults to `["adb"]` and may point at a remote-device/streaming wrapper, but the runner still passes the exact serial and never chooses the first device. Live credentials and artifact payloads stay in ignored `.local/` paths.

## Local authorization

`doctor` and `facts` are read-only. Every mutating scenario requires an `authorization` object with:

- an ISO-8601 expiry;
- an explicit allowed scenario;
- `allowApkInstall` for smoke/MVP/resilience;
- `allowProcessKill` for resilience;
- `allowReboot` when reboot is enabled;
- `allowControllerIsolation` when offline/online commands are configured.

Authorization is checked before the scenario and again at the adapter action. Missing, expired, or insufficient authorization exits 77 without intentionally mutating the device.

## Exclusive device lease

Every run acquires a non-blocking lease keyed by the configured serial hash under `.local/hil-locks/`. The holder record contains PID, scenario, evidence mode, task ID, source commit, and run directory. A second agent receives exit 77 rather than installing over or killing another run.

## Evidence modes

The default is diagnostic:

```sh
make hil-smoke HIL_BUILD=1
```

Diagnostic runs may use a dirty worktree and are permanently non-promotable. Candidate mode requires a clean tree and records `promotable: true` only after a PASS:

```sh
python3 tests/hil/run.py smoke --config .local/hil.json --build --mode candidate
```

A candidate run is necessary but not sufficient for gate promotion; every artifact still requires review and the final MVP seal must use one exact candidate APK.

## Deterministic local artifacts

For offline/private local testing, copy `tests/hil/artifact-set.example.json` into `.local/`, replace each path, digest, and size, and set `mvp.artifactSet` in `.local/hil.json`. Before VM apply, the runner:

1. verifies every local byte count and SHA-256;
2. skips an already active identical artifact;
3. uploads missing/different artifacts through `phonectl-mvp upload-image`;
4. records only artifact identities in evidence.

Public HTTPS import remains a separate `mvp.imageImports` path and retains its enrolled-origin/SSRF policy.

## Scenarios

```sh
make hil-smoke HIL_BUILD=1
make hil-mvp
make hil-resilience
make hil-all
```

SSH known-host state is isolated inside each run directory. Headscale identity assertions match exact node labels or their FQDN form, not arbitrary substrings. The MVP scenario restores guest mesh in a `finally` path and records cleanup success/failure.

`hil-resilience` has two distinct modes:

- with no isolation commands, it records a controller-silent smoke interval and leaves actual-unavailability skipped;
- with both offline/online commands and local authorization, it verifies the Host API becomes unavailable, the VM continues, and the controller path is restored.

## Evidence and promotion

Each run creates `.local/hil-runs/<run-id>/` containing source state, compact run record, APK digest, hashed device serial, per-run SSH trust, bounded redacted commands, device facts, and failure-only logcat. Smoke/MVP runs also record capabilities, profile versions, image digests, desired VM request, and before/after VM state.

Promotion is dry-run by default:

```sh
python3 tools/evidence/promote-hil.py \
  --run-dir .local/hil-runs/<run-id> \
  --gate B02 \
  --summary 'APK-native Alpine/QEMU smoke passed'

python3 tools/evidence/promote-hil.py ... --write
```

Promotion rejects diagnostic runs, dirty sources, invalid APK digests, commit mismatches, skipped required assertions, and explicitly non-promotable records. B11 remains intentionally manual because key-only SSH configuration needs additional direct evidence.

## Exit codes

- `0`: scenario passed.
- `1`: product assertion or exercised operation failed.
- `77`: required hardware, setup, authorization, or exclusive lease is unavailable.

Compatibility wrappers under `tests/device/` and `tests/e2e/` delegate here. Fake, emulator, and host-QEMU results cannot close physical gates.
