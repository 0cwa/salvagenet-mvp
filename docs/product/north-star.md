# SalvageNet product north star

## Authority and relationship to the current MVP

This document defines the durable SalvageNet product direction. `GOAL.md` defines the current bounded stock-Android/QEMU milestone and may deliberately exclude later platforms or product features. A milestone may narrow this north star; it must not silently replace it.

Planning outcomes and dependency order live in GitHub roadmap issues. `agents/task-dag.json` and the active packet remain the only implementation authorization. The acceptance ledger and reviewed evidence remain the only authority for validated claims.

## Mission

SalvageNet turns spare, retired, or underused devices into secure, remotely manageable Linux-capable nodes that can be attached to existing self-hosting and cluster-management systems with minimal setup.

The primary experience is:

1. install the APK or host service;
2. import or scan one authenticated provisioning configuration;
3. let SalvageNet prepare the best supported execution environment, private connectivity, identity, recovery path, and native orchestrator attachment;
4. manage applications through the selected upstream tools in their normal formats.

The product should make resilient self-hosting substantially more approachable without creating a simplified replacement for Docker Swarm mode, Kubernetes/K3s, Nomad, Nix, OpenTofu, Ansible, SSH, OCI, or normal Linux administration.

## Product boundary

SalvageNet owns the device-enablement layer:

- platform capability and trust evidence;
- durable host lifecycle, wake, power, thermal, storage, and recovery behavior;
- execution-environment selection and supervision;
- authenticated provisioning-capsule application;
- private-network and bootstrap integration;
- installation or activation of official upstream agents;
- native join, leave, drain, health, and diagnostics operations where supported;
- reversible updates and clear data ownership.

Upstream systems own:

- workloads, jobs, services, deployments, replicas, rollouts, and placement;
- cluster consensus and scheduling;
- application service discovery and ingress;
- native workload secrets and configuration;
- distributed application data and replication.

The Host API must not grow Kubernetes, Nomad, Swarm, Compose, Nix, or OpenTofu object models merely to present a common UI.

## Platform priority

Implementation and qualification priority is:

### A. Stock old Android phones through an APK

The ordinary APK remains the broad-access path. The first backend is the proven Podroid-derived ARM64 QEMU path. AVF may later accelerate supported devices. Stock Android limitations must be stated honestly: foreground-service, first-unlock, Doze, OEM process-management, VPN permission, thermal, charging, and storage behavior are reliability facts, not implementation details.

### B. Patched Android through `my-avbroot-setup`

The existing AVB patch workflow may install an optional, narrowly scoped system daemon and native Linux/container backend. This path should improve efficiency, boot persistence, networking, cgroup/namespace access, and reliability without becoming a requirement for stock devices or exposing a general-purpose root shell.

Hardware-backed Android key attestation, recognized custom AVB keys, lock state, boot measurements, APK identity, and signed build manifests should produce explicit trust tiers rather than a misleading trusted/untrusted boolean.

### C. ARM64 single-board computers

SBCs use a native Linux host service and may serve as stable workers, orchestrator managers, ingress nodes, routers, artifact caches, USB peers, and coordination servers. A device is manager-eligible only from measured power, storage, network, runtime, and trust facts.

### D. Existing Linux machines

Older computers should install the shared agent as a service and use the lightest suitable native process, OCI container, VM, or bounded microsandbox mode. SalvageNet must reuse systemd/OpenRC, Podman/containerd/Docker, QEMU, SSH, and existing packaging instead of recreating them.

### E. A dedicated Linux appliance image

A custom image follows concrete Android and Linux requirements. It should be reproducible, minimal, atomically updateable, recoverable, and compatible with native upstream agents; it should not become a new general-purpose distribution or package ecosystem.

### F. Windows through WSL

The Linux agent runs inside WSL. A small Windows bridge may own installation, startup, networking, and recovery. SalvageNet should not create a separate Windows workload model while the Linux environment can provide the required execution surface.

## One configuration, native formats

“One configuration” means one signed composition entry point, not one replacement schema for every tool.

A provisioning capsule may bind:

- authority and controller trust;
- runtime backend selection or `auto`;
- a profile or normalized bootable artifact by immutable identity;
- native Tailscale/Headscale or other overlay inputs;
- a native orchestrator attachment or external-provisioner reference;
- a named host power/resource policy;
- secret references rather than embedded permanent secrets.

The capsule must not describe workloads. Native configuration remains authoritative:

- Docker daemon settings and Swarm join operations;
- K3s configuration and Kubernetes resources;
- Nomad HCL and jobspecs;
- Nix modules and closures;
- OpenTofu provider resources;
- Ansible inventories and playbooks;
- ordinary SSH configuration.

The controller UI, Nix modules, OpenTofu modules, CLI, QR import, file import, and future APIs must compile to the same capsule and native artifacts.

## Offline and intermittently connected authority

The configuration authority may be a laptop that is offline most of the time. A node stores the last accepted signed configuration and continues its runtime and upstream agent without a controller lease.

Keep three roles distinct:

1. **Configuration authority:** authors and signs capsules, invitations, policies, and artifacts; may be offline.
2. **Bootstrap/discovery fabric:** locates nodes and immutable objects and reports bounded status; may be HTTPS initially and Zenoh later if evidence justifies it.
3. **Orchestrator control plane:** performs scheduling and HA through upstream managers/servers; must have the online quorum required by that orchestrator.

An offline laptop can be the first role and an administrator for the third. It cannot by itself provide continuous failure recovery when it is the only orchestrator manager.

## HA without hiding distributed-systems facts

SalvageNet should make resilient topologies easy to assemble and understand:

- prefer stable SBC/Linux/patched nodes for manager or server roles;
- treat stock phones as replaceable workers by default;
- label and taint devices from measured trust, power, storage, network, and thermal facts;
- generate native anti-affinity, spread, restart, update, and rollback guidance where appropriate;
- distinguish service continuity, control-plane availability, node-failure recovery, and data availability in the UI;
- never claim that replicas alone make state safe.

The first external product proof uses Docker Engine Swarm mode because its native worker attachment is small and auditable. K3s/Kubernetes and Nomad follow through the same attachment boundary. This order is an evidence strategy, not a claim that Swarm is the only or permanent orchestrator.

## Networking direction

Tailscale/Headscale is the first private overlay and should run in the Linux execution environment where practical, while the Android host retains an independent management/recovery identity in the current stock design.

Zenoh is a candidate optional bootstrap and discovery fabric for peer, client, router, cell-gateway, liveliness, query, and peer-assisted immutable-object retrieval use cases. It must not replace the overlay, become a CRDT desired-state database, or carry upstream workload state without a separate reviewed need.

USB-C networking remains an optional underlay. Stock Android may use Android Open Accessory user-space framing; patched Android may additionally expose native USB Ethernet. A missing cable must never remove the ordinary network or recovery path.

## Identity, community, and personal data

Future community enrollment may use signed, expiring QR invitations that bind an authenticated account, a device-generated key, attestation evidence, consent, and narrowly scoped roles. QR codes must not contain permanent cluster, overlay, or administrator credentials.

User-owned application data should compile to upstream placement, volume, backup, and application mechanisms. The UI must expose the unavoidable choices:

- local-only data maximizes physical locality but is unavailable with the device;
- local-primary plus encrypted backup improves recoverability;
- replicated HA improves availability but no longer stores the only physical copy on the owner's device.

SalvageNet should not build a custom distributed filesystem or promise row-level physical sharding for arbitrary applications.

## Architectural invariants

- One authoritative host supervisor per installed node agent.
- Desired state survives UI, service, process, network, and controller interruption within the guarantees of the platform tier.
- Typed operations; no public raw shell, QMP, QEMU/kernel arguments, or arbitrary host paths.
- Recovery remains independent from guest/workload networking.
- Host, execution environment, orchestrator node, account, and storage-owner identities remain distinct.
- Secrets are adapter-owned or referenced; diagnostics are bounded and redacted.
- Operations are authenticated, idempotent where practical, observable, reversible, and journaled across external side effects.
- Runtime and networking abstractions are proven by concrete second implementations, not invented speculatively.
- Qualified low-level tools are reused rather than replaced by agent-generated wrappers.
- Physical evidence is required for physical claims.

## Product proof ladder

1. **Validated stock-node substrate:** one exact APK and phone prove QEMU, host/guest connectivity, remote deployment, recovery, reboot, process, and offline-controller behavior.
2. **Turnkey cluster MVP:** one signed capsule turns that phone into a real Docker Swarm worker; a thin Slint controller and declarative modules drive the same flow; an unattended safety floor passes.
3. **Efficient Android tier:** `my-avbroot-setup` installs the native system backend and attestation policy.
4. **Stable heterogeneous fleet:** SBC, Linux, appliance, and WSL nodes implement the common execution-environment and attachment contracts.
5. **Orchestrator breadth:** K3s/Kubernetes and Nomad pass native join, drain, leave, outage, and recovery qualification.
6. **Community infrastructure:** scoped invitations, account-linked nodes, personal-data locality policies, and optional community-operated discovery services.

## Things SalvageNet should not build without new evidence

- a scheduler or cluster consensus system;
- a container runtime or VPN implementation;
- a universal workload/configuration schema;
- a mutable CRDT copy of upstream desired state;
- a new distributed filesystem;
- arbitrary root or shell RPC;
- a custom database where SQLite/PostgreSQL or upstream state is sufficient;
- a permanent compatibility layer for unpublished alpha formats;
- a complex plugin system before static adapters become a demonstrated constraint.
