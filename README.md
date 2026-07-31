# SalvageNet / NodeHost MVP

SalvageNet is an open-source device-enablement layer for turning spare Android phones and later SBC, Linux, appliance, and WSL hosts into secure Linux-capable nodes for existing self-hosting and cluster-management tools.

**NodeHost** is the current internal implementation name for the stock-Android host substrate. The current milestone preserves Podroid's APK-native QEMU path and proves durable remote provisioning, private host/guest connectivity, recovery, and Android lifecycle behavior. It is a host substrate, not a workload scheduler or cluster manager.

The durable direction is [`docs/product/north-star.md`](docs/product/north-star.md). The bounded current milestone is [`GOAL.md`](GOAL.md). The accepted evidence-driven order is [`docs/roadmap/strategic-priorities.md`](docs/roadmap/strategic-priorities.md).

> **Current maturity: device-lab candidate, not yet a validated stock-node substrate.**
>
> Automated software and packaging checks are substantially implemented. The active phase qualifies the canonical Ubuntu ARM64 guest boot independently of guest mesh and physical Android behavior; physical testing is next.

<!-- MVP-STATUS-BEGIN -->
**Acceptance:** 10/20 base gates passed; 10 are blocked on physical-device validation. USB networking remains deferred until every base gate passes.
<!-- MVP-STATUS-END -->

See [`docs/STATUS.md`](docs/STATUS.md) for the generated gate breakdown, [`docs/roadmap/podroid-mvp-alignment.md`](docs/roadmap/podroid-mvp-alignment.md) for the original-to-current bounded milestone mapping, and [`docs/roadmap/strategic-priorities.md`](docs/roadmap/strategic-priorities.md) for the path from physical proof to the turnkey cluster MVP.

## Product shape

```text
one signed provisioning configuration
        ↓
SalvageNet host layer
  stock Android / patched Android / SBC / Linux / appliance / WSL
        ↓
execution environment and private connectivity
        ↓
official upstream node agent
  Docker Swarm mode / K3s / Nomad / external provisioner
        ↓
native upstream workload and HA configuration
```

SalvageNet owns host lifecycle, backend selection, trust evidence, recovery, and native agent attachment. Docker, Kubernetes, Nomad, Nix, OpenTofu, Ansible, SSH, and application systems retain their normal formats and responsibilities.

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
- A live stable-ID GitHub roadmap synchronized with the active task DAG and generated public/agent snapshots.

## Active phase

```sh
make dev-plan
make dev-check
make status
make context TASK=H02A
```

H02A is the sole active task in phase `guest-boot-2`. It must prove one bounded canonical Ubuntu UEFI/QMP, NoCloud, key-only loopback SSH, restart, secret-hygiene, evidence, and cleanup flow on Linux host QEMU.

Guest Headscale/Tailscale enrollment remains H02B. Physical Android validation follows the bounded H02A result. Emulator work, Android process-death/runtime-ownership changes, Slint implementation, orchestrator attachment, patched Android, AVF, native rebuilds, Zenoh, and USB are not authorized by this phase.

The strategic roadmap adds queued outcomes only. It does not change `agents/task-dag.json`, acceptance status, or the physical critical path.

## Base work still requiring live evidence

The physical vertical slice must establish:

1. APK-native QEMU behavior on the target Android device;
2. host mesh and authenticated API reachability;
3. controller-driven Ubuntu deployment with a separate guest identity;
4. ordinary guest access plus the independent recovery route;
5. service, process, reboot, and controller-offline continuity.

A physical run during an implementation phase is useful diagnostic evidence. All gate-relevant scenarios must be rerun against one exact final candidate before the current milestone seal. Emulator, host-QEMU, packaging, issue, website, and code-review results cannot close physical gates.

## Next product proof

After B01–B20 are green, the next milestone proves SalvageNet rather than only the substrate:

1. compose and sign one narrow provisioning capsule;
2. import it through the controller;
3. turn the stock Android/QEMU node into a Docker Engine Swarm worker using native configuration;
4. run a real replicated service;
5. disconnect the configuration laptop without stopping the node;
6. drain, leave, replace, and rejoin;
7. present the flow through a thin Slint controller and Nix/OpenTofu composition modules;
8. pass a minimum unattended phone safety and continuity soak.

K3s, Nomad, patched Android, SBC/Linux/WSL, Zenoh, first-node Headscale/DDNS, and community/account features are visible later roadmap outcomes, not prerequisites for this proof.

## Start here

```sh
cat docs/product/north-star.md
cat GOAL.md
cat AGENTS.md
cat agents/task-dag.json
cat agents/tasks/H02A/task.md
cat docs/roadmap/strategic-priorities.md
cat docs/STATUS.md
make doctor
make dev-plan
make validate
```

## Repository map

| Need | Canonical source |
|---|---|
| Durable product direction and platform priorities | [`docs/product/north-star.md`](docs/product/north-star.md) |
| Current milestone and success conditions | [`GOAL.md`](GOAL.md) |
| Native orchestrator/configuration boundary | [`docs/architecture/turnkey-cluster-boundary.md`](docs/architecture/turnkey-cluster-boundary.md) |
| Runtime/platform expansion strategy | [`docs/architecture/platform-strategy.md`](docs/architecture/platform-strategy.md) |
| Priorities and sequencing | [`docs/roadmap/strategic-priorities.md`](docs/roadmap/strategic-priorities.md) |
| Original Podroid-MVP mapping and drift alarms | [`docs/roadmap/podroid-mvp-alignment.md`](docs/roadmap/podroid-mvp-alignment.md) |
| Current acceptance state | [`docs/STATUS.md`](docs/STATUS.md) |
| Active authorization | `agents/task-dag.json`, `agents/task-registry.json`, and the active packet |
| Roadmap planning truth | GitHub roadmap issues and dependencies; catalog under `.github/roadmap/` |
| Roadmap and human-aware agent workflow | [`docs/roadmap/public-roadmap-governance.md`](docs/roadmap/public-roadmap-governance.md), [`docs/development/roadmap-agent-workflow.md`](docs/development/roadmap-agent-workflow.md) |
| Current architecture and module boundaries | [`docs/architecture/overview.md`](docs/architecture/overview.md), [`docs/architecture/module-map.md`](docs/architecture/module-map.md) |
| Known debt and expiry triggers | [`docs/architecture/debt-register.md`](docs/architecture/debt-register.md) |
| Physical validation | [`tests/hil/README.md`](tests/hil/README.md), [`docs/roadmap/device-validation.md`](docs/roadmap/device-validation.md) |
| First-node Headscale/DDNS research | [`docs/research/headscale-bootstrap-ddns.md`](docs/research/headscale-bootstrap-ddns.md) |
| Complete documentation index | [`docs/INDEX.md`](docs/INDEX.md) |

## Historical material

The initial scaffold, overnight packets, completed task packets, superseded H02 packet, accepted W00 governance, and first roadmap bootstrap remain as provenance. They do not define current task authorization. The north star, bounded milestone, live roadmap, active DAG, acceptance ledger, and reviewed evidence are authoritative for their own concerns.
