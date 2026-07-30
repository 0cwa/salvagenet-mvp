# Foundation-first development roadmap

Physical Android evidence remains authoritative. Hardware-independent work exists only to make physical sessions less ambiguous and must not become an open-ended substitute for the vertical slice.

## Current repository state

| Task | State | Repository truth |
|---|---|---|
| F01 | **PLANNED** | Sole active task: make packaged JSON profiles and one strict artifact-manifest contract the Android production source of truth. |
| H01 | **MERGED** | Resumable authenticated artifact upload landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`; validated head run `30510377089` was fully green. |
| H02 | **QUEUED_REVIEW** | Guest QEMU/NoCloud/SSH/Headscale lab remains useful, but its scope and split must be reconsidered after F01. |
| H03 | **QUEUED_REVIEW** | Emulator lifecycle coverage remains useful, but its harness/scenario split must be reconsidered after F01. |
| H04 | **MERGED** | HIL evidence hardening landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. |

Only F01 appears in `agents/task-dag.json`. Queued and completed packets remain in the registry for provenance.

## Layered path

### Phase 0 — repository truth and planning discipline

**Purpose:** remove stale status, contradictory task authorization, and unverified future-task activation.

**Exit criteria:**

- H01 and H04 are recorded as merged with commit IDs.
- Completed tasks are absent from the active DAG.
- H02/H03 are queued for review rather than treated as pre-authorized parallel work.
- One active foundational packet has explicit entry, acceptance, verification, and phase-end criteria.
- The debt register, handoff, architecture docs, and development loop agree on the current state.

### Phase 1 — canonical artifact/profile foundation

**Active task:** F01.

**Purpose:** ensure Linux labs, emulator tests, Android runtime behavior, and uploaded artifacts use the same profile and manifest semantics.

**Exit criteria:** use the `foundation-1` criteria in `agents/task-dag.json` and the detailed F01 acceptance criteria. No physical gate changes in this phase.

### Phase 2 — deterministic preflight qualification

Activated only after the Phase 1 exit review.

Candidate work:

1. Guest boot, NoCloud, key-only SSH, restart, and secret-hygiene qualification under host QEMU.
2. Guest Headscale identity, tailnet SSH, control-server interruption, and recovery qualification.
3. Reproducible API 36 emulator harness if unit tests cannot cover the remaining lifecycle ambiguity.
4. Focused Activity/Service/Room/API lifecycle scenarios through real application ports.

H02 and H03 may be split, narrowed, run sequentially, or removed. They are not requirements merely because packets already exist.

### Phase 3 — physical vertical slice

Run through the existing `tests/hil/` implementation and bind every pass to an exact commit/APK.

1. **Device substrate:** B02, B08, B09 — APK-native QEMU boot, host Headscale, authenticated Host API.
2. **Guest vertical slice:** B10–B13 — uploaded Ubuntu image, apply generation, guest identity, ordinary SSH, recovery SSH.
3. **Durability:** B07, B16, B17 — Activity/service/process/reboot reconciliation and actual controller/network unavailability.
4. **MVP seal:** re-run the required scenarios against one exact final candidate and promote reviewed evidence.

### Phase 4 — post-base hardening

Only after the base vertical slice reveals real needs or all base gates pass:

- true qcow2 backing overlays or an honestly renamed copied-disk contract;
- project-owned native/runtime source builds and provenance;
- measured device resource admission;
- node-shell and mesh internal extraction where it reduces proven debugging/review cost;
- stronger controller authentication, durable controller implementation, and QEMU process isolation;
- strategic UI/shared-core decisions, including Slint/Rust, through explicit ADRs rather than accidental MVP coupling.

### Phase 5 — MVP+

AOA/USB link, TAP/NAT, second NIC, and fallback remain blocked until all B01–B20 gates are PASS.

## Simplicity rule

Do not keep a four-task wave active merely to maximize parallelism. Use the smallest active phase that resolves the next uncertainty. At each phase boundary, re-evaluate queued work and delete or rewrite plans whose assumptions are no longer true.
