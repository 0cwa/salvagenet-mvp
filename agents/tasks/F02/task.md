# F02 — Device-lab readiness and repository hygiene

## Status

**IN PROGRESS.** Work starts from `778feb4bf286d24774eadbf8a6ea0051c0f7a219` on `agent/F02-device-lab-readiness`.

## Outcome

Make the existing one-phone HIL runner safe and deterministic enough for supervised agent automation, while removing stale phase/root signals and recording larger runtime choices as decisions rather than premature implementation.

## Phase-start review

Impact-to-effort ordering:

1. Implement now: active-phase truth, root allowlist, exclusive device lease, expiring local action authorization, diagnostic/candidate evidence separation, clean-tree promotion, deterministic artifact upload, exact runtime-input capture, and guaranteed recovery cleanup.
2. Record now, implement later: guest classes, image/source selection, OCI artifact distribution, storage/update/power choices, and distro-family adapters.
3. Defer until evidence demands them: device farm, lab daemon, remote leases, network shaping, USB power switching, arbitrary container-to-VM conversion, and hostile-image claims.

F02 does not modify Android production behavior, QEMU arguments, VM profile schemas, controller authentication, mesh behavior, or acceptance-gate records.

## Allowed paths

See `allowed-paths.txt`. The task owns only repository metadata/docs, the HIL runner and promotion tool, Makefile HIL ergonomics, and one root-layout CI check.

## Acceptance criteria

- [ ] F01 is recorded as merged and F02 is the sole active task.
- [ ] Root-level implementation directories are allowlisted; placeholder-only `hostd/` and `usb-link/` roots are removed.
- [ ] The configured ADB serial is protected by a non-blocking local exclusive lease with holder metadata.
- [ ] Smoke/MVP/resilience actions require explicit, expiring, scenario-scoped local authorization.
- [ ] APK install, QEMU kill, reboot, and controller isolation are independently authorized at the adapter boundary.
- [ ] HIL defaults to diagnostic mode; only a clean candidate run can be promoted.
- [ ] Candidate evidence records source status, commit, APK digest, capabilities, profiles, images, desired VM, and before/after VM state.
- [ ] A local artifact-set file verifies size/digest and uploads through `phonectl-mvp upload-image` before VM apply.
- [ ] Guest mesh restoration is attempted in a `finally` path and cleanup outcome is recorded.
- [ ] Promotion rejects diagnostic, dirty, or explicitly non-promotable runs.
- [ ] Unit tests cover authorization, leasing, artifact-set validation, and promotion gating.
- [ ] Guest-class and OCI/image-source decisions plus phased roadmap are checked in.
- [ ] No physical gate changes status without reviewed physical evidence.

## Required checks

```sh
python3 -m unittest discover -s tests/hil -p 'test_*.py'
make validate
python3 tools/agents/verify-scope.py F02
make hil-doctor
```

When an authorized configured phone is available, run one diagnostic baseline:

```sh
make hil-smoke HIL_BUILD=1
```

A candidate run is permitted only after this branch is clean and the exact candidate is ready:

```sh
python3 tests/hil/run.py smoke --config .local/hil.json --build --mode candidate
```

## Phase-end verification

- [ ] Repository checks and HIL unit tests pass on the exact head.
- [ ] Root layout, task registry, DAG, README, and roadmap agree.
- [ ] Diagnostic evidence cannot pass promotion validation.
- [ ] A second process cannot lease the same configured device.
- [ ] Missing or expired authorization exits 77 without touching the device.
- [ ] Physical checks that could not run are reported honestly.

## Handoff

After F02 merges, review the narrowed deterministic Ubuntu UEFI/NoCloud boot-qualification task against the actual device-lab result. Keep guest mesh and emulator work separately queued. Do not begin OCI pulling or guest-class API changes until the base boot path has physical evidence and the checked-in ADR triggers are met.
