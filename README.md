# NodeHost MVP

NodeHost is an open-source Android host-enablement project built around a durable node supervisor and a profile-driven ARM64 QEMU runtime. It is a host substrate, not a workload scheduler or cluster manager.

> **Current maturity: device-lab candidate, not yet a validated MVP.**
>
> Automated software and packaging checks are substantially implemented. The current phase qualifies the canonical Ubuntu guest path on Linux host QEMU before guest mesh and physical Android validation.

<!-- MVP-STATUS-BEGIN -->
**Acceptance:** 10/20 base gates passed; 10 are blocked on physical-device validation. USB networking remains deferred until every base gate passes.
<!-- MVP-STATUS-END -->

See [`docs/STATUS.md`](docs/STATUS.md) for the generated gate breakdown, [`docs/roadmap/hardware-independent.md`](docs/roadmap/hardware-independent.md) for the active phase, and [`docs/roadmap/device-validation.md`](docs/roadmap/device-validation.md) for the physical evidence path.

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
make context TASK=H02A
```

H02A is the sole active task. It qualifies the canonical Ubuntu profile and artifact identities, UEFI/QMP boot, NoCloud, key-only loopback SSH, restart, secret hygiene, and bounded host-QEMU evidence. H02B guest mesh work and H03 emulator work remain queued for separate phase-start reviews.

F01, H01, and H04 are merged. Because there are no deployed pre-F01 installations, Ubuntu and AAVMF artifacts simply require active manifests; no compatibility migration code is retained.

## Base-MVP work still requiring live evidence

The physical vertical slice must establish:

1. APK-native QEMU behavior on the target Android device;
2. host mesh and authenticated API reachability;
3. controller-driven Ubuntu deployment with a separate guest identity;
4. ordinary guest access plus the independent recovery route;
5. service, process, reboot, and controller-offline continuity.

A physical run during an implementation phase is useful diagnostic evidence. All gate-relevant scenarios must be rerun against one exact final candidate before the MVP seal. Emulator, host-QEMU, packaging, and code-review results cannot close physical gates.

## Start here

```sh
cat GOAL.md
cat AGENTS.md
cat agents/task-dag.json
cat agents/tasks/H02A/task.md
cat docs/STATUS.md
make doctor
make dev-plan
make validate
```

## Repository map

| Need | Canonical source |
|---|---|
| Product boundary and success conditions | [`GOAL.md`](GOAL.md) |
| Current acceptance state | [`docs/STATUS.md`](docs/STATUS.md) |
| Active phase and queued work | [`docs/roadmap/hardware-independent.md`](docs/roadmap/hardware-independent.md), `agents/task-dag.json`, `agents/task-registry.json` |
| Architecture and module boundaries | [`docs/architecture/overview.md`](docs/architecture/overview.md), [`docs/architecture/module-map.md`](docs/architecture/module-map.md) |
| Known debt and expiry triggers | [`docs/architecture/debt-register.md`](docs/architecture/debt-register.md) |
| Physical validation | [`tests/hil/README.md`](tests/hil/README.md), [`docs/roadmap/device-validation.md`](docs/roadmap/device-validation.md) |
| Development loop | [`docs/development/development-loop.md`](docs/development/development-loop.md) |
| Complete documentation index | [`docs/INDEX.md`](docs/INDEX.md) |

## Historical material

The initial scaffold, overnight packets, completed F01/H01/H04 packets, and superseded H02 packet remain as provenance. They do not define current task authorization. The active phase metadata, acceptance ledger, generated status, and reviewed evidence are authoritative.
