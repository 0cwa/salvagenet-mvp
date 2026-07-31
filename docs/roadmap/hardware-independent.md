# Foundation-first development roadmap

Physical Android evidence remains authoritative. Hardware-independent work exists only to reduce implementation or validation ambiguity and must not become an open-ended substitute for the Podroid-fork MVP vertical slice.

## Current repository state

| Task | State | Repository truth |
|---|---|---|
| F01 | **MERGED** | Canonical packaged profiles and the strict active artifact-manifest contract landed at `246d551ca7e691a0319a4b30e29d6e4905cd9910`; final workflow `30549498423` passed. |
| H01 | **MERGED** | Resumable authenticated artifact upload landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`; validation run `30510377089` passed. |
| H02 | **SUPERSEDED** | The combined guest boot and guest mesh packet mixed separate failure domains and was split into H02A and H02B. |
| H02A | **PLANNED / ACTIVE** | Sole authorised task in `guest-boot-2`: canonical Ubuntu host-QEMU boot, QMP, NoCloud, key-only loopback SSH, restart, forbidden-material scan, evidence, and cleanup. |
| H02B | **QUEUED_REVIEW** | Guest Headscale identity, tailnet SSH, coordination interruption, and recovery. Requires H02A to pass. |
| H03 | **QUEUED_REVIEW** | Emulator infrastructure and lifecycle scenarios remain queued for a later value/cost review. |
| H04 | **MERGED** | HIL evidence hardening landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. |
| WEB04 | **MERGED** | Roadmap foundation merged at `888eb7e63a3419dca3f867d6baadbe95ef8c7e1f`; reviewed live snapshot merged at `15cc2791ebc6e81860fb73ca7a58e4ad12cf5235`. |

PR #19 merged at `b42c35ac17793fb1621baf19905a0eacea9b3521` after Actions run `30578924509`. It accepted `docs/roadmap/podroid-mvp-alignment.md`, ADR-012, complete roadmap governance, and the human-aware task-management contract.

WEB04 then materialised 30 labels, seven milestones, 53 stable-ID issues, and 82 dependency links. The reviewed live snapshot reports no fallback and no disagreements. GUEST-01 is issue #37 and is bound to `agents/tasks/H02A/task.md`.

Only H02A appears in `agents/task-dag.json`. Draft PR #20 remains a path-disjoint HIL safety review; it is not a prerequisite, a second authorised task, or physical evidence.

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
- the accepted plan for a static Astro website with one global token CSS system and System/Light/Dark theme control;
- GitHub Issues as roadmap planning truth after bootstrap;
- separate task authorization and acceptance authorities;
- compact, freshness-aware agent context with human-visible replanning.

### Phase 3 — issue roadmap and human-aware agent foundation

**Complete and merged.**

WEB04 delivered:

1. a reviewed complete stable-ID seed;
2. a human-visible exact-main bootstrap of labels, milestones, issues, and dependency links;
3. a live no-fallback public snapshot and compact agent index;
4. bounded status, freshness, sync, and per-issue context tools;
5. fail-closed structural validation and explicit disagreement reporting.

This enabling reordering made no Android, guest, physical, release, website, or acceptance claim.

### Phase 4 — deterministic guest boot

**Active task:** H02A.

H02A must prove one production-aligned host-QEMU flow before guest mesh or physical Android work resumes:

1. pin and verify the exact Ubuntu ARM64 cloud image;
2. consume the canonical packaged profile and rendered vendor-data rather than parallel definitions;
3. record exact AAVMF code/vars source paths, digests, sizes, and package/tool facts;
4. derive or verify the QEMU command shape against the canonical profile;
5. prove real QMP `running`, NoCloud completion, and key-only loopback SSH;
6. prove a clean guest reboot and a complete QEMU stop/start;
7. scan bounded seed, cloud-init, log, environment, and temporary state for forbidden bootstrap material;
8. capture machine-readable `host-qemu` evidence and remove generated keys, seed media, PID/socket files, and temporary state.

The phase explicitly excludes Headscale/Tailscale guest enrollment, Android process-death/runtime-ownership changes, AVF, emulator work, physical gate claims, website implementation, native-runtime rebuilds, and USB.

### Phase 5 — queued preflight candidates

After H02A evidence, reconsider rather than auto-activate:

1. **H02B:** one-use guest Headscale enrollment, distinct guest identity, tailnet SSH, `tailscaled` restart, interruption, and recovery.
2. **Runtime-presence investigation:** only if physical Android evidence shows a QEMU child can remain live or ambiguous after app-process loss; study PID/start-time ownership, authenticated QMP probing, and stale-endpoint cleanup without importing a second supervisor authority.
3. **Emulator harness/scenarios:** only if remaining Android lifecycle ambiguity justifies the cost.
4. **Website foundation/content:** follow the live roadmap and remain path-disjoint from the product critical path when separately authorised.

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

Use the smallest phase that resolves the next uncertainty. Do not import a parallel supervisor, VM manager, management transport, profile authority, or speculative compatibility system merely because another fork implemented one. A larger mechanism must be justified by current evidence, a concrete security/correctness failure, or a present validation blocker. Delete compatibility code and task scope that have no real users, evidence need, or near-term product value.
