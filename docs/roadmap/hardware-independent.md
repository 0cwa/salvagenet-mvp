# Foundation-first development roadmap

Physical Android evidence remains authoritative. Hardware-independent work exists only to make physical sessions less ambiguous and must not become an open-ended substitute for the vertical slice.

## Current repository state

| Task | State | Repository truth |
|---|---|---|
| F01 | **MERGED** | Canonical packaged profiles and the strict active artifact-manifest contract landed at `246d551ca7e691a0319a4b30e29d6e4905cd9910`. Final head `31dcd75199928b7887132a1429392266388c0b60` passed Actions run `30549498423`. |
| H01 | **MERGED** | Resumable authenticated artifact upload landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`; validated head run `30510377089` was fully green. |
| H02 | **SUPERSEDED** | The combined guest boot and guest mesh packet mixed separate failure domains and was split into H02A and H02B. |
| H02A | **PLANNED** | Sole active task: canonical Ubuntu UEFI/QMP, NoCloud, loopback SSH, restart, and secret-hygiene qualification on host QEMU. |
| H02B | **QUEUED_REVIEW** | Guest Headscale identity, tailnet SSH, coordination interruption, and recovery. Requires H02A to pass. |
| H03 | **QUEUED_REVIEW** | Emulator infrastructure and lifecycle scenarios remain queued for a later value/cost review. |
| H04 | **MERGED** | HIL evidence hardening landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. |

Only H02A appears in `agents/task-dag.json`. Merged, superseded, and queued packets remain in the registry for provenance.

## Layered path

### Phase 0 — repository truth and planning discipline

**Complete.**

Exit evidence:

- Completed work is absent from the active DAG.
- Future tasks are queued rather than treated as pre-authorized parallel work.
- Each active phase has explicit entry, acceptance, verification, and phase-end criteria.
- The registry, roadmap, handoff, debt register, and agent goal agree on current authorization.

### Phase 1 — canonical artifact/profile foundation

**Complete and merged.**

F01 established:

- strict, bounded packaged JSON as the production profile source;
- byte-for-byte canonical profile, schema, index, and guest-init assets in the APK;
- runtime rejection of vendor-data path traversal;
- one strict active-manifest contract for artifact publication, listing, cleanup, installed checks, and runtime consumption;
- manifest-only Ubuntu/AAVMF resolution, while the three pinned Podroid qualification assets retain their deliberate bare-file contract;
- one verified source resolution per disk preparation, 1 MiB streaming copies, and copied-byte digest verification;
- static guards against reintroducing complete Kotlin profile mirrors or duplicate manifest parsers.

Because the app has no deployed pre-F01 installations, the unused Ubuntu/AAVMF compatibility migration was removed rather than preserved as permanent complexity.

Final F01 evidence:

```text
mergeCommit: 246d551ca7e691a0319a4b30e29d6e4905cd9910
validatedHead: 31dcd75199928b7887132a1429392266388c0b60
workflowRun: 30549498423
workflowArtifactId: 8762334271
workflowArtifactDigest: sha256:6163f03ca995a366f6e2d47a53e9d70c33adce23eaf0dd80e76ea212351da868
apkSha256: f423bd939f97be119250318ca1c871df0ff9bc25a67b0e5672cc75c6d668e7f9
hardwareValidated: false
```

### Phase 2 — deterministic guest boot qualification

**Active task:** H02A.

The phase-start review fixed the boundary before implementation. H02A covers only:

1. canonical Ubuntu profile and guest-init identity;
2. pinned Ubuntu and AAVMF artifact identity;
3. UEFI boot and real QMP `running` status;
4. NoCloud completion;
5. key-only SSH through loopback SLIRP;
6. guest reboot and complete QEMU stop/start;
7. guest disk/log/process/temp inspection for retained one-use credentials or callback capabilities;
8. bounded machine-readable host-QEMU evidence explicitly marked non-Android.

This phase does not include Headscale or Tailscale guest enrollment. It first proves the guest image/bootstrap path independently of mesh behavior.

### Phase 3 — queued preflight candidates

These tasks are not active merely because their predecessors existed:

1. **H02B — guest mesh qualification:** one-use Headscale enrollment, separate guest identity, tailnet SSH, `tailscaled` restart, coordination interruption, and recovery. Requires successful H02A evidence and a fresh phase-start review.
2. **Stateless emulator harness:** deterministic API 36 create/boot/install/execute/collect/destroy. Activate only if the remaining lifecycle ambiguity justifies its cost.
3. **Emulator lifecycle scenarios:** Activity, Service, Room, enrollment, permission, and Host API behavior through real ports with release-surface exclusion. Requires a proven emulator harness.

At each boundary, re-evaluate whether queued work still reduces physical-debugging ambiguity. Split, narrow, reorder, or remove it rather than preserving stale scope.

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

Do not keep a multi-task wave active merely to maximize parallelism. Use the smallest phase that resolves the next uncertainty. At every boundary, delete compatibility code and task scope that have no real users, evidence need, or near-term product value.
