# Foundation-first development roadmap

Physical Android evidence remains authoritative. Hardware-independent work exists only to make physical sessions less ambiguous and must not become an open-ended substitute for the vertical slice.

## Current repository state

| Task | State | Repository truth |
|---|---|---|
| F01 | **MERGED** | Canonical profile/manifest foundation merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910`; final head `31dcd75199928b7887132a1429392266388c0b60` passed Actions run `30549498423`. |
| H01 | **MERGED** | Resumable authenticated artifact upload landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`. |
| H02 | **PLANNED / ACTIVE** | Narrowed to canonical Ubuntu guest boot, NoCloud, key-only loopback SSH, restart, secret hygiene, and bounded host-QEMU evidence. |
| H03 | **QUEUED_REVIEW** | Emulator work remains queued behind an explicit phase-start review and demonstrated need. |
| H04 | **MERGED** | HIL evidence hardening landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. |

Only H02 appears in `agents/task-dag.json`. Completed and queued packets remain in the registry for provenance, not authorization.

## Layered path

### Phase 0 — repository truth and planning discipline

**Complete.** Completed work is absent from the active DAG, queued plans are not pre-authorized, and phase entry/exit verification is enforced.

### Phase 1 — canonical artifact/profile foundation

**Complete.** F01 made packaged checked-in profile data and one strict artifact-manifest adapter the Android production source of truth. It made no physical acceptance claim.

Unreleased development-state compatibility is not a product requirement. Cleanup of any unnecessary pre-release migration path is separate scoped work and must leave the canonical resolver simple.

### Phase 2 — deterministic guest boot qualification

**Active task:** H02.

The task proves:

1. canonical Ubuntu profile and locked artifact identity;
2. UEFI boot and real QMP `running` status;
3. NoCloud/cloud-init completion;
4. key-only SSH through loopback SLIRP;
5. clean QEMU stop/start and guest restart;
6. inspection of guest disk, cloud-init state, logs, and temporary metadata for retained one-use credentials or callback capabilities;
7. bounded machine-readable host-QEMU evidence explicitly marked non-Android.

This phase excludes Headscale enrollment. It first proves the image/bootstrap path independently of mesh behavior.

### Phase 3 — queued preflight candidates

These tasks are not active merely because broad predecessor plans existed:

1. **Guest mesh qualification** — one-use Headscale enrollment, separate guest identity, tailnet SSH, `tailscaled` restart, Headscale interruption, and recovery. Requires successful H02 guest boot qualification.
2. **Stateless emulator harness** — deterministic API 36 create/boot/install/execute/collect/destroy. Activate only when remaining lifecycle ambiguity justifies its cost.
3. **Emulator lifecycle scenarios** — Activity, Service, Room, enrollment, permission, and Host API behavior through real ports with release-surface exclusion. Requires a proven emulator harness.

At each boundary, re-evaluate whether queued work still reduces physical-debugging ambiguity. Split, narrow, reorder, or remove it rather than preserving stale scope.

### Phase 4 — physical vertical slice

Run through the existing `tests/hil/` implementation and bind every pass to an exact commit/APK.

1. **Device substrate:** B02, B08, B09 — APK-native QEMU boot, host Headscale, authenticated Host API.
2. **Guest vertical slice:** B10–B13 — uploaded Ubuntu image, apply generation, guest identity, ordinary SSH, recovery SSH.
3. **Durability:** B07, B16, B17 — Activity/service/process/reboot reconciliation and actual controller/network unavailability.
4. **MVP seal:** re-run required scenarios against one exact final candidate and promote reviewed evidence.

### Phase 5 — post-base hardening

Only after the base vertical slice reveals real needs or all base gates pass:

- project-owned native/runtime source builds and provenance;
- measured device resource admission;
- node-shell and mesh internal extraction where it reduces proven debugging/review cost;
- stronger controller authentication, durable controller implementation, and QEMU process isolation;
- strategic UI/shared-core decisions through explicit ADRs rather than accidental MVP coupling.

Contract corrections that make names match current behavior may happen earlier when the project is still unreleased and the correction prevents tests from qualifying a knowingly false contract.

### Phase 6 — MVP+

AOA/USB link, TAP/NAT, second NIC, and fallback remain blocked until all B01–B20 gates are PASS.

## Simplicity and compatibility rule

Use the smallest active phase that resolves the next uncertainty. Delete or rewrite plans whose assumptions are no longer true.

The project is unreleased alpha. Reset disposable development state rather than adding migration or dual-format production paths. Any real future compatibility requirement must be explicitly authorized, isolated from canonical code, bounded by a support window, and assigned a deletion trigger.
