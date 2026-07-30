# Foundation-first development roadmap

Physical Android evidence remains authoritative. Hardware-independent work exists only to make physical sessions safer and less ambiguous and must not become an open-ended substitute for the vertical slice.

## Current repository state

| Task/change | State | Repository truth |
|---|---|---|
| F01 | **MERGED** | Canonical packaged profiles and one strict artifact-manifest contract merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910`. |
| Podroid vendoring hardening | **MERGED** | External composition hook and reproducible patch queue merged at `778feb4bf286d24774eadbf8a6ea0051c0f7a219`. |
| F02 | **IN_PROGRESS** | Sole active task: safe deterministic HIL automation and repository/root truth. |
| H02 | **QUEUED_REVIEW** | Broad predecessor remains queued; only deterministic Ubuntu guest boot qualification should be activated after F02. |
| H03 | **QUEUED_REVIEW** | Emulator work remains queued until a phase-start review shows it reduces physical ambiguity. |
| H01/H04 | **MERGED** | Authenticated resumable upload and HIL evidence foundations are present. |

Only F02 appears in `agents/task-dag.json`. Queued and completed packets remain in the registry for provenance.

## Phase 0 — repository truth and planning discipline

Complete. Completed work is removed from the active DAG, queued work is not pre-authorized, and task packets define bounded scope.

## Phase 1 — canonical artifact/profile foundation

Complete through F01. Android production loads strict packaged JSON, artifact producers/consumers share one manifest contract, and preparation verifies exact bytes.

## Phase 2 — Podroid vendoring boundary

Complete through PR #8. The upstream subtree is pinned and reproducible from an ordered patch queue; SalvageNet composition and packaging live outside the subtree.

## Phase 3 — device-lab readiness

Active as F02. Prioritize high impact-to-effort safeguards:

1. serial-specific exclusive lease;
2. expiring local scenario/action authorization;
3. diagnostic versus clean candidate evidence;
4. deterministic local artifact verification/upload;
5. exact profile/image/desired-state evidence;
6. cleanup guarantees;
7. root-layout and phase-truth checks;
8. durable guest/image decisions without implementation scope creep.

This phase may run diagnostic `hil-doctor`/`hil-smoke`, but it changes no acceptance gate by itself.

## Phase 4 — deterministic guest boot qualification

Activate only after F02 merges and a new packet is reviewed. Cover canonical Ubuntu artifact identity, UEFI boot, real QMP status, NoCloud completion, key-only loopback SSH, clean stop/start/restart, and retained-secret inspection. Keep Headscale enrollment separate until boot/bootstrap is proven.

## Phase 5 — physical vertical slice

Run through `tests/hil/` and bind every pass to one clean candidate commit/APK:

1. device substrate: APK-native QEMU, host mesh, authenticated Host API;
2. guest slice: uploaded Ubuntu image, desired generation, guest identity, ordinary SSH, recovery SSH;
3. durability: Activity/service/process/reboot reconciliation and actual controller/network unavailability;
4. final rerun against one exact candidate before promotion.

## Phase 6 — post-base hardening and product expansion

Only after base evidence reveals a need or all base gates pass: true qcow2 overlays, project-owned native builds, resource admission, runtime isolation, durable controller/UI decisions, guest-class/image binding, source providers, and representative distro adapters.

USB/AOA remains MVP+ and has no placeholder implementation root until activated.
