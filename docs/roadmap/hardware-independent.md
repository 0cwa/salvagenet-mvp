# Foundation-first development roadmap

Physical Android evidence remains authoritative. Hardware-independent work exists only to make physical sessions less ambiguous and must not become an open-ended substitute for the vertical slice.

## Current repository state

| Task | State | Repository truth |
|---|---|---|
| F01 | **MERGE_READY** | Canonical profile/manifest foundation and verified pre-F01 Ubuntu/AAVMF migration passed the full workflow at head `71a04acedd11221fbefe2c0fa43984141ec11ed4`, run `30543765626`. The final documentation head still requires the same workflow before merge. |
| H01 | **MERGED** | Resumable authenticated artifact upload landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`; validated head run `30510377089` was fully green. |
| H02 | **QUEUED_REVIEW** | Original broad guest QEMU/NoCloud/SSH/Headscale packet is superseded. Only guest boot qualification should be activated after F01 merges. |
| H03 | **QUEUED_REVIEW** | Original broad emulator packet is superseded and remains queued behind an explicit phase-start review. |
| H04 | **MERGED** | HIL evidence hardening landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. |

Only F01 appears in `agents/task-dag.json` until PR #7 merges. Queued and completed packets remain in the registry for provenance.

## Layered path

### Phase 0 — repository truth and planning discipline

**Complete.**

Exit evidence:

- H01 and H04 are recorded as merged with commit IDs.
- Completed tasks are absent from the active DAG.
- H02/H03 were queued for review rather than treated as pre-authorized parallel work.
- One active foundational packet had explicit entry, acceptance, verification, and phase-end criteria.
- The debt register, handoff, architecture docs, and development loop agreed on the current state.

### Phase 1 — canonical artifact/profile foundation

**Task:** F01 — merge ready.

**Purpose:** ensure Linux labs, emulator tests, Android runtime behavior, and uploaded artifacts use the same profile and manifest semantics.

Verified result:

- Android production profile resolution loads strict, bounded packaged JSON rather than duplicated Kotlin definitions.
- The APK contains byte-for-byte canonical profiles, schema, index, and rendered guest-init assets.
- Artifact publication, listing, cleanup, installed checks, and runtime consumption use one strict manifest contract.
- Steady-state bare-file resolution is limited to the three pinned Podroid qualification artifacts.
- A complete digest-verified pre-F01 Ubuntu/AAVMF bare bundle migrates once into active manifests; an isolated bare non-Podroid artifact fails closed.
- H01, HTTPS importer, QEMU, Android, guest, package, signature, 16 KiB alignment, and artifact checks passed at implementation head `71a04acedd11221fbefe2c0fa43984141ec11ed4`, Actions run `30543765626`.

The phase closes only when the final documentation head passes the same workflow and the exact tested head is merged. No physical gate changes in this phase.

### Phase 2 — deterministic guest boot qualification

Activate only after F01 merges and a new phase packet is reviewed against the merged result.

The sole first active task should cover:

1. canonical Ubuntu profile and pinned artifact identity;
2. UEFI boot and real QMP status;
3. NoCloud completion;
4. key-only SSH through loopback SLIRP;
5. clean QEMU stop/start and guest restart;
6. inspection of guest disk, cloud-init state, logs, and temporary metadata for retained one-use credentials or callback capabilities;
7. bounded machine-readable host-QEMU evidence explicitly marked non-Android.

This phase must not include Headscale enrollment. It first proves the guest image/bootstrap path independently of mesh behavior.

### Phase 3 — queued preflight candidates

These tasks are not active merely because their broad predecessors existed:

1. **Guest mesh qualification** — one-use Headscale enrollment, separate guest identity, tailnet SSH, `tailscaled` restart, Headscale interruption, and recovery. Requires successful guest boot qualification.
2. **Stateless emulator harness** — deterministic API 36 create/boot/install/execute/collect/destroy. Activate only when the remaining lifecycle ambiguity justifies its cost.
3. **Emulator lifecycle scenarios** — Activity, Service, Room, enrollment, permission, and Host API behavior through real ports with release-surface exclusion. Requires a proven emulator harness.

At each boundary, re-evaluate whether the queued work still reduces physical-debugging ambiguity. Split, narrow, reorder, or remove it rather than preserving stale scope.

### Phase 4 — physical vertical slice

Run through the existing `tests/hil/` implementation and bind every pass to an exact commit/APK.

1. **Device substrate:** B02, B08, B09 — APK-native QEMU boot, host Headscale, authenticated Host API.
2. **Guest vertical slice:** B10–B13 — uploaded Ubuntu image, apply generation, guest identity, ordinary SSH, recovery SSH.
3. **Durability:** B07, B16, B17 — Activity/service/process/reboot reconciliation and actual controller/network unavailability.
4. **MVP seal:** re-run the required scenarios against one exact final candidate and promote reviewed evidence.

### Phase 5 — post-base hardening

Only after the base vertical slice reveals real needs or all base gates pass:

- true qcow2 backing overlays or an honestly renamed copied-disk contract;
- project-owned native/runtime source builds and provenance;
- measured device resource admission;
- node-shell and mesh internal extraction where it reduces proven debugging/review cost;
- stronger controller authentication, durable controller implementation, and QEMU process isolation;
- strategic UI/shared-core decisions, including Slint/Rust, through explicit ADRs rather than accidental MVP coupling.

### Phase 6 — MVP+

AOA/USB link, TAP/NAT, second NIC, and fallback remain blocked until all B01–B20 gates are PASS.

## Simplicity rule

Do not keep a four-task wave active merely to maximize parallelism. Use the smallest active phase that resolves the next uncertainty. At each phase boundary, re-evaluate queued work and delete or rewrite plans whose assumptions are no longer true.
