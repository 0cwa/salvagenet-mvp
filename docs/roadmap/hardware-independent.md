# Foundation-first development roadmap

Physical Android evidence remains authoritative. Hardware-independent work exists only to reduce implementation or validation ambiguity and must not become an open-ended substitute for the Podroid-fork MVP vertical slice.

## Current repository state

| Task | State | Repository truth |
|---|---|---|
| F01 | **MERGED** | Canonical packaged profiles and the strict active artifact-manifest contract landed at `246d551ca7e691a0319a4b30e29d6e4905cd9910`; final workflow `30549498423` passed. |
| H01 | **MERGED** | Resumable authenticated artifact upload landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`; validation run `30510377089` passed. |
| H02 | **SUPERSEDED** | The combined guest boot and guest mesh packet mixed separate failure domains and was split into H02A and H02B. |
| H02A | **QUEUED_REVIEW** | Reviewed canonical Ubuntu guest-boot task, paused without implementation for the bounded WEB04 foundation. |
| H02B | **QUEUED_REVIEW** | Guest Headscale identity, tailnet SSH, coordination interruption, and recovery. Requires H02A to pass. |
| H03 | **QUEUED_REVIEW** | Emulator infrastructure and lifecycle scenarios remain queued for a later value/cost review. |
| H04 | **MERGED** | HIL evidence hardening landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. |
| WEB04 | **PLANNED** | Sole active task: bootstrap the GitHub issue roadmap, last-known-good snapshot, compact agent index, and bounded context tooling. |

PR #19 merged at `b42c35ac17793fb1621baf19905a0eacea9b3521` after Actions run `30578924509`. It accepted `docs/roadmap/podroid-mvp-alignment.md`, ADR-012, complete roadmap governance, and the human-aware task-management contract.

Only WEB04 appears in `agents/task-dag.json`. H02A is not superseded and no H02A implementation is discarded.

## Layered path

### Phase 0 — repository truth and planning discipline

**Complete.**

Completed work is historical, future work is queued by default, phase transitions are reviewed, and unreleased-alpha compatibility requires explicit authorization rather than automatic migration code.

### Phase 1 — canonical artifact/profile foundation

**Complete and merged.**

F01 established canonical packaged profiles, guest-init assets, a strict active-manifest contract, verified artifact copying, and static guards against duplicate profile/manifest sources.

### Phase 2 — accepted product and public-surface governance

**Complete and merged.**

W00/PR #19 established:

- an explicit mapping from the original Podroid-fork MVP to current implementation choices;
- drift alarms protecting APK-native QEMU, separate host/guest identity, typed APIs, recovery, one VM, and USB deferral;
- a static Astro website with one global token CSS system and System/Light/Dark theme control;
- GitHub Issues as roadmap planning truth after bootstrap;
- separate task authorization and acceptance authorities;
- compact, freshness-aware agent context with human-visible replanning.

### Phase 3 — issue roadmap and human-aware agent foundation

**Active task:** WEB04.

The user selected task-management infrastructure before website implementation. WEB04 is intentionally short and bounded:

1. create and validate the complete stable-ID seed;
2. materialize labels, milestones, issues, and real dependency links idempotently;
3. generate a last-known-good public snapshot and compact agent index;
4. add bounded status, freshness, sync, and per-issue context tools;
5. report disagreement among issue, task, PR, and acceptance state instead of hiding it.

This is an enabling reordering, not a product-direction change. It makes no Android, guest, physical, release, or website claim.

### Phase 4 — deterministic guest boot and website foundation

At WEB04 phase end, run a fresh review. The expected shape is:

- **H02A reactivated:** canonical Ubuntu UEFI/QMP, NoCloud, key-only loopback SSH, restart, and secret-hygiene qualification;
- **WEB01 optionally authorised in parallel:** Astro shell, global design tokens/CSS, layout components, theme control, and component gallery.

These tasks may run together only when their write paths are disjoint and the live roadmap/index is healthy. H02A remains the product critical path; WEB01 must not consume Android/QEMU/profile ownership.

### Phase 5 — queued preflight candidates

After H02A evidence, reconsider rather than auto-activate:

1. **H02B:** one-use guest Headscale enrollment, distinct guest identity, tailnet SSH, `tailscaled` restart, interruption, and recovery.
2. **Emulator harness/scenarios:** only if remaining Android lifecycle ambiguity justifies the cost.
3. **Website content/status/enhancements:** WEB02–WEB06 follow the generated graph and design-system foundation; they do not alter product acceptance.

### Phase 6 — physical vertical slice

Run through `tests/hil/` and bind every pass to an exact commit/APK:

1. **Device substrate:** B02, B08, B09 — APK-native QEMU boot, host Headscale, authenticated Host API.
2. **Guest vertical slice:** B10–B13 — controller-delivered Ubuntu, generation apply, guest identity, ordinary SSH, recovery SSH.
3. **Durability:** B07, B16, B17 — Activity/service/process/reboot reconciliation and actual controller/network unavailability.
4. **MVP seal:** rerun required scenarios against one exact final candidate and promote reviewed evidence.

Agent-safe device-lab lease/authorization/evidence work may improve this runner when separately reviewed, but it cannot close a physical gate by itself.

### Phase 7 — early access and post-base work

After the base MVP:

- close release licensing/notices/corresponding-source requirements before public APK distribution;
- publish verified downloads, device records, and tested guides;
- qualify thermal, storage, network, OEM, and update behaviour;
- consider stronger QEMU isolation, reviewed controller authentication, Rust/Slint controller, Linux hosts, guest-class/image-source separation, more profiles, and other platform expansion from evidence.

### MVP+

AOA/USB control, stream NIC, TAP/NAT, fallback, and optional artifact transfer remain blocked until all B01–B20 gates are PASS.

## Simplicity rule

Use the smallest phase that resolves the next uncertainty. A bounded governance/tooling phase may temporarily pause a ready product task when it prevents duplicated roadmap state and enables safe parallel work, but it must record the pause and restore the product critical path at phase end. Delete compatibility code and task scope that have no real users, evidence need, or near-term product value.
