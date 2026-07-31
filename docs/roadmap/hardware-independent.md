# Foundation-first development roadmap

Physical Android evidence remains authoritative. Hardware-independent work exists only to reduce implementation or validation ambiguity and must not become an open-ended substitute for the stock-Android/QEMU vertical slice.

The durable product direction is `docs/product/north-star.md`; the accepted strategic order is `docs/roadmap/strategic-priorities.md`. The active phase and task are always read from `agents/task-dag.json`.

## Current repository state

| Task | State | Repository truth |
|---|---|---|
| F01 | **MERGED** | Canonical packaged profiles and the strict active artifact-manifest contract are production truth. |
| H01 | **MERGED** | Resumable authenticated artifact upload is implemented and validated in software. |
| H02 | **SUPERSEDED** | The combined guest boot and guest mesh packet mixed separate failure domains and was split into H02A and H02B. |
| H02A | **ACTIVE when present in DAG** | Canonical Ubuntu host-QEMU boot, QMP, NoCloud, key-only loopback SSH, restart, forbidden-material scan, evidence, and cleanup. |
| H02B | **QUEUED_REVIEW** | Guest Headscale identity, tailnet SSH, coordination interruption, and recovery. Requires H02A to pass and a fresh phase review. |
| H03 | **QUEUED_REVIEW** | Emulator infrastructure and lifecycle scenarios remain queued for a later value/cost review. |
| H04 | **MERGED** | The single HIL evidence path is implemented; physical scenarios remain authoritative. |
| WEB04 | **MERGED** | GitHub issue roadmap, dependency graph, generated public snapshot, compact agent index, and bounded context tooling exist. |

The strategic catalog extends the reviewed roadmap with queued turnkey, platform, networking, and community outcomes. It does not change the active DAG or the acceptance ledger.

## Layered path

### Phase 0 — repository truth and planning discipline

**Complete.**

Durable direction, current milestone, GitHub planning, active authorization, and acceptance evidence are separate authorities. Future work is queued by default and phase transitions are reviewed.

### Phase 1 — canonical artifact/profile foundation

**Complete and merged.**

F01 established canonical packaged profiles, guest-init assets, a strict active-manifest contract, verified artifact copying, and guards against duplicate profile/manifest sources.

### Phase 2 — roadmap and agent context foundation

**Complete and merged.**

The live roadmap provides stable-ID issues, dependency links, reviewed metadata, a strict generated projection, and bounded per-issue context. Catalog generations can add accepted outcomes without rewriting first-bootstrap provenance. Issue state does not authorize work and issue closure does not change acceptance.

### Phase 3 — deterministic guest boot

**Active task:** derive from `agents/task-dag.json`; currently H02A.

H02A must prove one production-aligned host-QEMU flow before guest mesh or physical Android work resumes:

1. pin and verify the exact Ubuntu ARM64 cloud image;
2. consume the canonical packaged profile and rendered vendor-data rather than parallel definitions;
3. record exact AAVMF code/vars source paths, digests, sizes, and package/tool facts;
4. derive or verify the QEMU command shape against the canonical profile;
5. prove real QMP `running`, NoCloud completion, and key-only loopback SSH;
6. prove a clean guest reboot and a complete QEMU stop/start;
7. scan bounded seed, cloud-init, log, environment, and temporary state for forbidden bootstrap material;
8. capture machine-readable `host-qemu` evidence and remove generated keys, seed media, PID/socket files, and temporary state.

The phase excludes Headscale/Tailscale guest enrollment, Android process-death/runtime-ownership changes, AVF, emulator work, physical gate claims, Slint, orchestrator attachment, patched Android, native-runtime rebuilds, Zenoh, and USB.

### Phase 4 — phase-boundary decision

After H02A evidence, reconsider rather than auto-activate:

1. **H02B:** only if one-use guest Headscale enrollment and recovery preflight remain the highest-value ambiguity;
2. **physical DEVICE-01:** preferred when the host-QEMU result makes the phone path actionable;
3. **runtime-presence investigation:** only if physical evidence shows ambiguous QEMU ownership after process loss;
4. **emulator scenarios:** only if repeated lifecycle ambiguity justifies their maintenance;
5. **path-disjoint public/release work:** only through separate authorization and without delaying hardware.

### Phase 5 — physical stock-node vertical slice

Run through `tests/hil/` and bind every pass to an exact commit/APK:

1. **Device substrate:** B02, B08, B09 — APK-native QEMU boot, host Headscale, authenticated Host API.
2. **Guest vertical slice:** B10–B13 — controller-delivered Ubuntu, generation apply, guest identity, ordinary SSH, recovery SSH.
3. **Durability:** B07, B16, B17 — Activity/service/process/reboot reconciliation and actual controller/network unavailability.
4. **Milestone seal:** rerun required scenarios against one exact final candidate and promote reviewed evidence.

Agent-safe device-lab lease/authorization/evidence work may improve this runner when separately reviewed, but it cannot close a physical gate by itself.

### Phase 6 — turnkey cluster product proof

After B01–B20 pass, activate the smallest reviewed sequence:

1. MVP-01 signed provisioning capsule and native attachment contract;
2. MVP-02 physical Docker Engine Swarm worker proof;
3. MVP-03 thin Slint controller;
4. MVP-04 Nix/OpenTofu composition modules;
5. MVP-05 minimum unattended safety and continuity floor.

This milestone proves the user-facing product without requiring K3s, Nomad, patched Android, multi-platform support, Zenoh, community accounts, or USB.

### Phase 7 — early access and reliability

Resolve release licensing/notices/corresponding source before public APK distribution. Publish exact downloads, guided setup, tested recovery, and device records only after the substrate and turnkey proof are evidence-bound.

Then broaden thermal, storage, network, OEM, update, and device-class qualification.

### Phase 8 — platform and orchestrator expansion

Follow the accepted priority:

1. generic execution-environment contract;
2. `my-avbroot-setup` native Android backend and attestation;
3. SBC;
4. existing Linux;
5. custom Linux appliance;
6. WSL;
7. real K3s and Nomad attachments;
8. optional Zenoh and first-node Headscale/DDNS experiments;
9. community identity, data policies, and DDNS service.

### MVP+ USB

AOA/USB control, stream NIC, TAP/NAT, fallback, and optional artifact transfer remain blocked until every B01–B20 gate is PASS. A phase review may order USB relative to post-base product work, but USB cannot become a prerequisite for the ordinary stock-node or orchestrator proof.

## Simplicity rule

Use the smallest phase that resolves the next uncertainty. Do not import a parallel supervisor, runtime manager, management transport, profile authority, cluster model, storage system, or speculative compatibility layer merely because another implementation exists.

A larger mechanism must be justified by current evidence, a concrete security/correctness failure, or a present product-proof blocker. Delete compatibility code and task scope that have no real users, evidence need, or near-term value.
