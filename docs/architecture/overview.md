# Architecture overview

## Scope

This page describes the **current stock-Android/QEMU implementation**. The durable multi-platform product boundary is `docs/product/north-star.md`; the native orchestrator/configuration boundary is `docs/architecture/turnkey-cluster-boundary.md`; later runtime/platform direction is `docs/architecture/platform-strategy.md`.

The current Android application authenticates a controller, manages one QEMU VM, provides a recovery route, and hands guest configuration to SSH/Ansible or other normal tools. It is not a scheduler or cluster manager.

```text
Controller / phonectl
        |
        | typed authenticated Host API over host mesh
        v
Android NodeSupervisorService
        |
        +-- desired/observed reconciler + operation journal
        +-- embedded host Tailscale adapter
        +-- artifact store + profile resolver
        +-- Podroid-derived QEMU adapter
        +-- recovery SSH tunnel
        |
        v
QEMU ARM64 guest
        |
        +-- cloud-init/profile bootstrap
        +-- independent guest Tailscale identity
        +-- ordinary OpenSSH
        +-- later native upstream agent provisioning
```

## Combined architectural styles

### Modular monolith

One Android APK and one authoritative supervisor process. Modules are compile-time boundaries, not independently deployed Android services. QEMU remains a child process because it is a real isolation and lifecycle boundary.

This is the current platform shape. Later patched Android and Linux hosts may have a system daemon or native service while preserving one authoritative supervisor for each installed host agent.

### Onion / ports and adapters

`node-model` and `node-core` are the center. Android, Room, QEMU, Tailscale, Ktor, Podroid, and filesystems are outer adapters. Dependency arrows point inward.

### Reconciler

The controller writes desired generations. The node observes actual state, plans stable steps, journals intent, applies effects, re-observes, and records the result.

The controller is not a runtime lease. The last accepted desired state remains authoritative while the controller is unavailable.

### Event-driven observation

Android lifecycle, QMP events, process exits, network changes, artifact progress, and guest readiness enter as typed observations. Events wake reconciliation; they do not directly redefine desired state.

### Request/response control

The external Host API is resource-oriented request/response with durable operation resources. It is not an internal event bus and not an arbitrary command gateway.

## Permanent cross-platform contracts

- stable node identity and controller authorization;
- signed accepted intent and durable operation lifecycle;
- desired/observed reconciliation independent of UI/controller lifetime;
- replaceable runtime, overlay, bootstrap, and attachment adapters;
- typed lifecycle and artifact operations;
- system/data ownership separation;
- recovery route independent from workload/guest health;
- normal native administration and orchestrator interfaces inside the execution environment;
- bounded, redacted diagnostics and explicit trust/capability facts.

## Current VM-specific contracts

The following remain correct for the bounded current milestone but should not be treated as permanent names for every backend:

- `/v1/vms` and VM desired generations;
- QEMU profile and image resources;
- QMP shutdown/observation;
- loopback-forwarded guest recovery SSH;
- one active VM.

PLAT-16 owns the later additive execution-environment vocabulary after the stock node and first external orchestrator proofs. Do not refactor these names during H02A or before physical evidence unless a reviewed blocker requires it.

## Current implementation caveats

F01 closed the profile and artifact source-of-truth split: production loads canonical packaged JSON and all non-Podroid artifacts require strict active manifests. Only the pinned Podroid qualification inputs retain their deliberate bare-file contract.

The current active uncertainty is integration rather than architecture: H02A must prove that the canonical Ubuntu profile, rendered NoCloud vendor-data, selected cloud image, and recorded host firmware boot repeatably under Linux host QEMU before the physical Android path resumes.

Kotlin, Compose, Hilt, Python `phonectl`, Ktor, Room, and libtailscale are current implementations behind intended boundaries. They are not permission to couple domain contracts to those tools or to preclude later Slint/Rust/shared-host decisions.

## Current milestone constraint

One active VM and qualified ARM64 profiles only. This is a deliberate bounded product constraint, not a requirement that later patched Android, SBC, Linux, appliance, or WSL backends masquerade as VMs.
