# NodeHost MVP

NodeHost is the internal implementation name for the open-source SalvageNet Android host-enablement project. It is built around a durable node supervisor and a profile-driven ARM64 QEMU runtime. It is a host substrate, not a workload scheduler or cluster manager.

> **Current maturity: device-lab candidate, not yet a validated MVP.**
>
> Automated software and packaging checks are substantially implemented. The current bounded phase bootstraps the issue roadmap and human-aware agent state before website implementation; H02A remains the next product-critical guest-boot qualification task.

<!-- MVP-STATUS-BEGIN -->
**Acceptance:** 10/20 base gates passed; 10 are blocked on physical-device validation. USB networking remains deferred until every base gate passes.
<!-- MVP-STATUS-END -->

See [`docs/STATUS.md`](docs/STATUS.md) for the generated gate breakdown, [`docs/roadmap/podroid-mvp-alignment.md`](docs/roadmap/podroid-mvp-alignment.md) for the original-to-current MVP mapping, and [`docs/roadmap/hardware-independent.md`](docs/roadmap/hardware-independent.md) for the active phase and next product work.

## Current implementation

- Podroid-derived APK-packaged QEMU integration with typed command compilation and QMP lifecycle control.
- Durable desired state and operation journal.
- Canonical packaged Alpine, Ubuntu, and K3s-readiness profiles.
- One strict active-manifest contract for non-Podroid artifacts.
- Typed authenticated Host API, controller client, guest bootstrap, and recovery path.
- Embedded Android-aware host mesh plus a separate guest identity.
- Authenticated resumable artifact delivery and a hardened public import path.
- Static, JVM, Android, guest, packaging, signature, alignment, and evidence checks.
- One physical HIL runner under `tests/hil/`.

## Active phase

```sh
make dev-plan
make dev-check
make status
make context TASK=WEB04
```

WEB04 is the sole active task after the phase-transition PR merges. It creates the complete GitHub issue graph, last-known-good roadmap snapshot, compact agent index, and bounded per-issue context before the website is implemented.

H02A is paused, not superseded. It remains the next product-critical task and must receive a fresh phase-start review after WEB04. The expected next phase may pair reactivated H02A with path-disjoint WEB01 website-foundation work.

## Base-MVP work still requiring live evidence

The physical vertical slice must establish:

1. APK-native QEMU behavior on the target Android device;
2. host mesh and authenticated API reachability;
3. controller-driven Ubuntu deployment with a separate guest identity;
4. ordinary guest access plus the independent recovery route;
5. service, process, reboot, and controller-offline continuity.

A physical run during an implementation phase is useful diagnostic evidence. All gate-relevant scenarios must be rerun against one exact final candidate before the MVP seal. Emulator, host-QEMU, packaging, issue, website, and code-review results cannot close physical gates.

## Start here

```sh
cat GOAL.md
cat AGENTS.md
cat agents/task-dag.json
cat agents/tasks/WEB04/task.md
cat docs/roadmap/podroid-mvp-alignment.md
cat docs/STATUS.md
make doctor
make dev-plan
make validate
```

## Repository map

| Need | Canonical source |
|---|---|
| Product boundary and success conditions | [`GOAL.md`](GOAL.md) |
| Original Podroid-MVP mapping and drift alarms | [`docs/roadmap/podroid-mvp-alignment.md`](docs/roadmap/podroid-mvp-alignment.md) |
| Current acceptance state | [`docs/STATUS.md`](docs/STATUS.md) |
| Active phase and queued work | [`docs/roadmap/hardware-independent.md`](docs/roadmap/hardware-independent.md), `agents/task-dag.json`, `agents/task-registry.json` |
| Roadmap and human-aware agent workflow | [`docs/roadmap/public-roadmap-governance.md`](docs/roadmap/public-roadmap-governance.md), [`docs/development/roadmap-agent-workflow.md`](docs/development/roadmap-agent-workflow.md) |
| Architecture and module boundaries | [`docs/architecture/overview.md`](docs/architecture/overview.md), [`docs/architecture/module-map.md`](docs/architecture/module-map.md) |
| Known debt and expiry triggers | [`docs/architecture/debt-register.md`](docs/architecture/debt-register.md) |
| Physical validation | [`tests/hil/README.md`](tests/hil/README.md), [`docs/roadmap/device-validation.md`](docs/roadmap/device-validation.md) |
| Public website plan | [`website/README.md`](website/README.md) |
| Complete documentation index | [`docs/INDEX.md`](docs/INDEX.md) |

## Historical material

The initial scaffold, overnight packets, completed F01/H01/H04 packets, superseded H02 packet, and accepted W00 governance remain as provenance. They do not define current task authorization. The active phase metadata, live roadmap after bootstrap, acceptance ledger, generated status, and reviewed evidence are authoritative for their own concerns.
