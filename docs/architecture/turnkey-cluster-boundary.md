# Turnkey cluster and native-configuration boundary

## Purpose

SalvageNet should make a heterogeneous device immediately provisionable without becoming another workload orchestrator. This document defines the small first-party layer required to connect platform lifecycle, private networking, and upstream node agents while reusing their native configuration and HA behavior.

## System roles

```text
Configuration authority
  laptop, CI, or delegated signer; may be offline
        |
        | signed immutable provisioning capsule
        v
SalvageNet host agent
  Android APK / patched daemon / SBC / Linux / WSL
        |
        +-- execution environment
        +-- overlay and recovery
        +-- native attachment materialization
        +-- lifecycle, power, thermal, storage, diagnostics
        v
Official upstream agent
  Docker Engine Swarm mode / K3s / Nomad / external provisioner
        |
        v
Upstream control plane and native workload formats
```

The configuration authority is not a runtime lease. The node persists the last accepted capsule and continues the execution environment and upstream agent when the laptop or bootstrap service is unavailable.

The upstream control plane remains subject to its own quorum rules. SalvageNet may recommend stable managers and report risk, but it cannot create scheduling HA while every manager/server is offline.

## Provisioning capsule

The common capsule is deliberately narrow and versioned. Its conceptual fields are:

```json
{
  "apiVersion": "salvagenet.io/v1alpha1",
  "kind": "NodeAttachment",
  "metadata": {
    "name": "office-phone-worker",
    "revision": 12
  },
  "authority": {
    "issuer": "ed25519:...",
    "expiresAt": "..."
  },
  "runtime": {
    "backend": "auto",
    "profile": "oci://registry.example/nodeos@sha256:..."
  },
  "connectivity": {
    "driver": "tailscale",
    "nativeConfig": "oci://registry.example/overlay@sha256:..."
  },
  "attachment": {
    "type": "docker-swarm-worker",
    "nativeConfig": "oci://registry.example/swarm-worker@sha256:..."
  },
  "hostPolicy": "plugged-in-balanced"
}
```

The exact encoding may be canonical JSON, CBOR/COSE, or another reviewed signed representation. Human-authored YAML, Nix, OpenTofu, the Slint UI, QR import, and CLI flags are input surfaces; they should compile to one canonical representation.

### Capsule invariants

- Immutable revision and content digest.
- Authenticated issuer and bounded validity.
- Rollback/downgrade policy.
- Secret references rather than permanent secret values where possible.
- No arbitrary shell, argv, QEMU arguments, kernel arguments, or host paths.
- No workloads, services, deployments, jobs, replicas, or generic volume model.
- Native configuration may be opaque to the common layer, but the responsible adapter validates its expected type, size, origin, digest, and lifecycle.
- Last accepted capsule remains locally available when the authority is offline.

## Native attachment contract

A first-party attachment adapter has a small responsibility:

1. declare required host/runtime capabilities;
2. materialize or reference the upstream agent and native configuration;
3. retrieve or redeem narrowly scoped enrollment material;
4. invoke the upstream join/start operation;
5. report native health and identity;
6. invoke native cordon/drain/leave behavior where supported;
7. remove transient enrollment material;
8. preserve existing workloads when the authority disappears.

It does not parse or own upstream workload state.

Conceptually:

```text
AttachmentDriver
├── requirements()
├── prepare(native_config_ref)
├── join(enrollment_ref)
├── status()
├── drain(policy)
├── leave()
└── recover()
```

The interface should be derived from concrete Docker Swarm, K3s, and Nomad behavior. Do not add fields merely to make the adapters appear symmetrical.

## Generic external-provisioner mode

Turnkey support for “something else” should not require a built-in adapter for every cluster manager.

A generic external-provisioner attachment may:

- ensure the execution environment and private/recovery access are ready;
- publish stable inventory, addresses, host keys, capabilities, and data paths;
- authorize a controller key or CA;
- expose idempotent lifecycle and artifact operations;
- let OpenTofu, Nix, Ansible, SSH, or another native client perform the rest.

First-class adapters are justified when SalvageNet can make join, leave, health, recovery, and user guidance materially safer or simpler without importing the tool's workload model.

## Initial orchestrator order

### Docker Engine Swarm mode

Use Docker Engine's user-facing Swarm mode, not raw SwarmKit embedding. The proof should use the Docker Engine API or carefully bounded CLI operations to:

- prepare `daemon.json` without replacing unrelated user settings;
- start a compatible Docker Engine;
- redeem a worker-scoped join credential;
- join a manager endpoint;
- confirm node certificate and active state;
- run a replicated service placed by Swarm;
- survive configuration-authority interruption;
- drain, leave, replace, and rejoin.

Stable SBC/Linux/patched nodes may later be manager-eligible. Stock phones default to workers. Three or five managers are the normal HA recommendation; existing tasks may keep running after manager quorum is lost, but scheduling and management stop until quorum returns.

### K3s/Kubernetes

Use the official K3s agent and native K3s configuration. Phones default to agents, while stable nodes host server/datastore roles. Qualification should cover:

- cgroups, namespaces, storage, networking, DNS, and kernel prerequisites;
- native `config.yaml` materialization;
- join and certificate rotation;
- node labels/taints from measured host facts;
- cordon, drain, leave, reconnect, and controller interruption;
- CNI/MTU behavior over the selected underlay.

Kubernetes manifests, Helm values, Operators, and workloads remain upstream configuration.

### Nomad

Use the official Nomad client and native HCL. Qualification must account for privileged Linux client requirements and the licensing/distribution decision. It should cover native task drivers, disconnected-client behavior, drain, leave, rejoin, and any server-dependent templates or secrets that alter offline continuity.

Nomad jobspecs and server state remain outside SalvageNet.

## Nix and OpenTofu composition

Nix and OpenTofu belong on the controller/build side.

### Nix

Use Nix modules to compose and pin:

- APK and host-service builds;
- `my-avbroot-setup` modules;
- normalized NodeOS/guest artifacts;
- native overlay and orchestrator configuration;
- host-policy presets;
- signed capsule output;
- Linux/appliance system configuration.

Nix is the reference reproducible compiler, not a phone runtime requirement.

### OpenTofu

Start with modules using existing providers for DNS, Tailscale where appropriate, registries, secrets, cloud resources, Kubernetes, Helm, Nomad, and other infrastructure.

Do not start with a first-party provider. A SalvageNet provider becomes justified when the controller owns real remote resources such as:

- enrolled device records;
- capsule assignment;
- attestation state;
- update rings;
- revocation;
- community invitation resources.

Avoid `remote-exec` as the normal provisioning mechanism. OpenTofu should publish or assign immutable intent, while the node reconciles locally.

## Networking planes

Keep these separate:

1. **Physical underlay:** Wi-Fi, cellular, Ethernet, USB, or other links.
2. **Private overlay:** Tailscale/Headscale initially; another provider only after a concrete adapter proves the boundary.
3. **Bootstrap/discovery:** HTTPS initially; optional Zenoh later for peers, routers, queries, liveliness, and immutable-object location.
4. **Host management/recovery:** authenticated Host API and bounded recovery channel.
5. **Orchestrator control:** upstream manager/server traffic.
6. **Workload network:** Docker overlay, CNI, application protocols, ingress, and storage traffic.

Zenoh must not silently merge these planes. It may improve discovery and intermittent-controller behavior while the capsule signature and upstream control plane remain authoritative.

## Offline behavior

When the configuration authority is unavailable:

- the host keeps the last accepted desired state;
- the execution environment keeps running;
- the overlay and upstream node agent reconnect using their own state;
- existing workloads follow upstream local runtime behavior;
- no new capsule revision is accepted unless signed by an authorized delegated key;
- the node reports bounded status when a management path returns.

When the orchestrator control plane is unavailable, existing workloads may continue according to the upstream system, but new scheduling, replacement, scaling, and many changes stop. The UI must describe that as service continuity, not full HA.

## Data and storage boundary

The capsule may name persistent data boundaries and host policies, but application storage remains native:

- Docker volumes and application-native replication;
- Kubernetes PV/PVC/CSI and node affinity;
- Nomad host/CSI volumes;
- Nix-managed paths;
- standard backup tools and object stores.

SalvageNet may generate native placement and backup guidance. It must not invent a generic cross-orchestrator distributed volume API until a concrete unsupported need is demonstrated.

## Security boundaries

- The configuration root may be offline and delegate narrower signing roles.
- Enrollment credentials are scoped, short-lived, and erased after use.
- Controller and cluster-manager credentials are not stored in guest images or public capsules.
- Node identity, host-management identity, guest/agent identity, account identity, and storage-owner identity are distinct.
- Attestation is evidence and policy input, not authorization by itself.
- Runtime trust depends on backend: AVF/QEMU isolation, patched system containers, and native Linux have different threat models.
- A capsule source or cache need not be trusted when the object is content-addressed and signature-verified.

## MVP proof boundary

The current B01–B20 milestone proves the stock node substrate. The next product proof must additionally establish:

1. one signed capsule;
2. one physical stock Android node;
3. one official Docker Engine Swarm worker join;
4. one real replicated service;
5. configuration-laptop interruption without workload loss;
6. native drain, leave, and rejoin;
7. a thin Slint controller using the same contracts as CLI and declarative modules;
8. a minimum unattended safety/continuity soak.

No Kubernetes, Nomad, Zenoh, patched Android, multi-user account system, personal-storage system, or USB feature should be required to call that proof successful.
