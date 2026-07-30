# Architecture overview

## Product boundary

The Android application is a node-enablement and execution-environment manager. It authenticates a controller, manages one QEMU VM, provides a recovery route, and then hands guest configuration to SSH/Ansible or other normal tools. It is not a scheduler or cluster manager.

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
        +-- later Ansible-installed workloads/orchestrators
```

## Combined architectural styles

### Modular monolith

One Android APK and one authoritative supervisor process. Modules are compile-time boundaries, not independently deployed Android services. QEMU remains a child process because it is a real isolation and lifecycle boundary.

### Onion / ports and adapters

`node-model` and `node-core` are the center. Android, Room, QEMU, Tailscale, Ktor, Podroid, and filesystems are outer adapters. Dependency arrows point inward.

### Reconciler

The controller writes desired generations. The node observes actual state, plans stable steps, journals intent, applies effects, re-observes, and records the result.

### Event-driven observation

Android lifecycle, QMP events, process exits, network changes, artifact progress, and guest readiness enter as typed observations. Events wake reconciliation; they do not directly redefine desired state.

### Request/response control

The external Host API is resource-oriented request/response with durable operation resources. It is not an internal event bus and not an arbitrary command gateway.

## Permanent contracts

- stable device identity and controller authorization;
- typed profile and desired runtime generation;
- durable operation lifecycle;
- replaceable runtime and mesh adapters;
- recovery route independent from guest health;
- normal SSH endpoint inside the guest.

## Current implementation caveats

F01 closed the profile and artifact source-of-truth split: production loads canonical packaged JSON and all non-Podroid artifacts require strict active manifests. Only the three pinned Podroid qualification inputs retain their deliberate bare-file contract.

The current active uncertainty is integration rather than architecture: H02A must prove that the canonical Ubuntu profile, rendered NoCloud vendor-data, selected cloud image, and recorded host firmware boot repeatably under Linux host QEMU before guest mesh behavior is added.

Kotlin, Compose, Hilt, Python `phonectl`, Ktor, Room, and libtailscale are current MVP implementations behind intended boundaries. They are not permission to couple domain contracts to those tools or to preclude later Slint/Rust/shared-controller decisions.

## MVP constraint

One active VM and qualified ARM64 profiles only. This is a deliberate product limit, not a hidden assumption in the domain model.
