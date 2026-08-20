# ADR-013: Separate the SalvageNet north star from the current substrate milestone

- **Status:** Proposed
- **Date:** 2026-07-31
- **Decision owners:** SalvageNet maintainers

## Context

The repository began as a bounded Podroid-fork MVP intended to prove that an ordinary ARM64 Android phone could boot and durably manage a remotely provisioned QEMU guest. `GOAL.md`, the B01–B20 ledger, and the initial roadmap correctly optimized for that proof.

Subsequent product research established a broader durable direction:

- one authenticated configuration should turn a device into a node that existing orchestrators can provision;
- upstream Docker Swarm mode, K3s/Kubernetes, Nomad, Nix, OpenTofu, Ansible, SSH, and native formats should remain authoritative;
- the configuration authority may be an intermittently connected laptop;
- platform priority is stock Android, patched Android, SBC, existing Linux, custom Linux appliance, then WSL;
- patched Android should use `my-avbroot-setup` as a first-class optional backend and support explicit attestation tiers;
- a thin Slint controller and declarative composition should provide the user-facing setup path;
- Zenoh, first-node Headscale/DDNS, QR/account enrollment, and personal-data locality are accepted future research directions, not current requirements.

Using the original Podroid milestone as the highest product authority would either omit these directions or incorrectly make them look like drift. Adding all of them to the current active phase would instead derail the imminent physical proof.

The initial GitHub roadmap catalog also encoded a fixed first-bootstrap inventory. Rewriting that historical seed would obscure provenance, while leaving cardinality permanently hard-coded would prevent the live issue graph from representing accepted later outcomes.

## Decision

### 1. Separate durable direction from bounded milestone

- `docs/product/north-star.md` defines durable product direction.
- `GOAL.md` defines the current stock-Android/QEMU substrate milestone.
- Milestone exclusions are not interpreted as rejection of accepted north-star outcomes.
- Changes to either authority require explicit review, but they answer different questions.

### 2. Preserve current authorization and evidence

- H02A remains the sole active task while present in `agents/task-dag.json`.
- The next implementation step remains physical Android validation through the existing HIL runner.
- Strategic roadmap publication adds queued/hold outcomes only.
- B01–B20 remain the exact acceptance ledger for the current substrate milestone.

### 3. Add a distinct turnkey cluster product proof

After the current substrate passes, the next milestone proves:

1. a signed provisioning capsule that references native configuration;
2. a real Docker Engine Swarm-mode worker on the physical stock Android node;
3. configuration-laptop interruption without stopping existing service;
4. native drain, leave, replacement, and rejoin;
5. a thin Slint provisioning controller;
6. Nix/OpenTofu composition modules;
7. a minimum unattended safety/continuity floor.

Docker Engine Swarm mode is the first evidence target because its native worker-join surface is small. This does not make Swarm the only or permanent orchestrator.

### 4. Preserve native upstream authority

The common capsule may bind authority, runtime/profile, connectivity, native attachment, and host policy. It contains no workloads, services, jobs, deployments, replicas, or generic cluster-resource model.

First-party adapters may install/activate official agents, materialize native configuration, join, report health, drain, leave, and recover. Upstream systems own scheduling and workload state.

### 5. Expand the GitHub roadmap through catalog generations

- `.github/roadmap/seed.v1.json` remains immutable first-bootstrap provenance.
- `.github/roadmap/expansion.v1.json` adds accepted strategic items and reviewed dependency/context updates.
- `tools/roadmap/catalog.py` composes generations and derives expected item/milestone sets from reviewed catalog data.
- The existing exact-main apply workflow materializes missing GitHub issues and dependencies after merge.
- Live issues remain planning truth after apply; the composed catalog retains reviewed metadata and completeness coverage.
- The active issue label and `agents/task-dag.json` must remain synchronized.

### 6. Record platform and research order without authorizing it

The roadmap records:

- patched Android system backend and attestation;
- SBC, existing Linux, custom appliance, and WSL;
- K3s and Nomad attachments;
- optional Zenoh bootstrap/discovery evaluation;
- optional first-node Headscale/DDNS bootstrap;
- community QR/account enrollment, data locality policy, and DDNS service.

These items default to queued or hold and cannot be implemented until a reviewed phase transition creates an active packet.

## Consequences

### Positive

- Physical testing remains the immediate critical path.
- Agents receive the complete product context without loading every future issue.
- The current QEMU work becomes a strong first backend rather than the implicit definition of every platform.
- The first product proof demonstrates actual upstream orchestration instead of only VM management.
- Native formats and mature tools remain authoritative, limiting agent-generated configuration and management bloat.
- Roadmap history remains auditable while later accepted outcomes can be added cleanly.

### Costs and risks

- The project now has two product-direction documents that must remain clearly scoped.
- Catalog expansion requires an exact-main apply after the code/docs PR merges; strict live projection is intentionally incomplete between those two reviewed states.
- Existing issue wording may need later human edits where first-bootstrap summaries are narrower than the new context metadata.
- The Host API remains VM-shaped through the current physical milestone; PLAT-16 must broaden it additively before later backends depend on permanent VM terminology.
- Swarm, Slint, Nix/OpenTofu, and safety-soak work add another milestone before broad early access.

## Rejected alternatives

### Rewrite the current MVP to include every platform and orchestrator

Rejected because it would delay the highest-value physical evidence and create speculative abstractions before one phone works.

### Keep the Podroid MVP as the permanent product authority

Rejected because accepted patched-Android, heterogeneous-host, one-config, offline-authority, and community goals would remain invisible or be treated as drift.

### Create a universal orchestrator schema

Rejected because it would duplicate native configuration and move workload-management semantics into SalvageNet.

### Replace Tailscale/Headscale immediately with Zenoh

Rejected because the systems address different layers and Zenoh has not yet demonstrated enough value to justify adding another distributed runtime to the current phone path.

### Rewrite the first roadmap seed

Rejected because it would destroy bootstrap provenance and make later decisions appear historical.

## Review and expiry

Review this ADR after:

- the stock substrate is sealed;
- MVP-02 completes the first external orchestrator proof;
- PLAT-16 is ready to generalize public runtime terminology;
- or evidence shows the capsule/attachment boundary is insufficient.

If the Swarm proof reveals a different upstream system is materially simpler or safer, the milestone may substitute that system through a reviewed roadmap/ADR change while preserving the native-attachment principle.
