# Tool and dependency radar

This radar separates durable product boundaries from current implementations and accepted later evaluations. A roadmap entry does not authorize dependency adoption; the active packet must name the dependency, boundary, evidence, license, maintenance, and removal path.

## Core product contracts

These are implementation-independent commitments:

- one authoritative host supervisor and desired/observed reconciliation;
- durable operation journal around external effects;
- signed, immutable provisioning intent with native-config references;
- typed lifecycle, artifact, diagnostics, recovery, and attachment operations;
- separate host, execution-environment, orchestrator, account, and storage-owner identities;
- normal upstream agents and workload formats remain authoritative;
- system/data ownership separation;
- offline configuration authority is not a runtime lease;
- physical evidence for physical claims.

## Core for the current stock-Android milestone

- Kotlin and Android SDK for lifecycle/platform integration.
- Podroid-derived APK-native QEMU execution contract.
- JSON profile, enrollment, artifact-manifest, and OpenAPI contracts.
- SQLite operation/current-state persistence semantics.
- Tailscale/Headscale host and guest connectivity with independent recovery.

These are current milestone commitments, not claims that every later host is Android or every execution environment is a VM.

## Adopted for the current candidate

- Jetpack Compose, Hilt, coroutines/StateFlow.
- Room 2.8.x.
- QEMU/TCG, QMP, `qemu-img`, libslirp.
- Official Android-aware libtailscale integration and pinned Go toolchain.
- Ktor CIO 3.x as the first Host API adapter.
- cloud-init NoCloud.
- Headscale 0.28.x laboratory and first coordination provider.
- OpenSSH and Ansible at the guest boundary.
- Python `phonectl` only as the temporary validation controller.

Do not rewrite these during H02A or before physical evidence identifies a blocker.

## Adopt for the turnkey cluster MVP after the stock substrate

### Docker Engine Swarm mode

Use Docker Engine's supported Swarm mode and native API/configuration. Do not embed or fork SwarmKit. The first proof is a worker join, service placement, offline-authority continuity, drain, leave, replacement, and rejoin.

### Slint and Rust controller

Use Slint for the thin cross-platform provisioning/diagnostics controller after the capsule contract is accepted. Use Rust for the controller core where it reduces desktop/Linux duplication. Do not make the physical Android proof depend on an Android UI rewrite.

### Nix and OpenTofu modules

Use Nix as a reproducible build/composition option and OpenTofu modules with existing providers. Keep both controller-side. Do not create a first-party provider until SalvageNet owns real remote resources that modules cannot model cleanly.

### Canonical signed capsule

Use a compact versioned representation with existing cryptographic and artifact standards. Evaluate canonical JSON or CBOR/COSE, TUF delegation/rollback protection, and OCI/ORAS distribution. Avoid a universal workload schema.

## Evaluate behind proven contracts

- AVF as an additional stock-Android VM backend.
- `my-avbroot-setup` system daemon and a maintained native Linux/container foundation for patched Android.
- Android hardware-backed key attestation and custom AVB build-manifest matching.
- Rust shared host agent for SBC, Linux, appliance, and WSL.
- systemd/OpenRC packages, Podman/containerd/runc/LXC, and QEMU according to platform capabilities.
- Ignition or existing declarative appliance foundations after Linux requirements settle.
- K3s official agent and native configuration.
- Nomad official client and native HCL, subject to capability and licensing review.
- Nebula or another structurally different private-overlay provider only to prove the mesh boundary.
- Zenoh as an optional bootstrap/discovery/query/liveliness fabric after the stock and Swarm proofs.
- provider-neutral dynamic DNS adapters for first-node Headscale bootstrap.
- direct SQLite instead of Room where shared implementation or SQL control justifies it.
- mTLS/principal authorization replacing the temporary bearer capability.

## Hold

- multiple active execution environments;
- generic third-party profile marketplace;
- dynamic native plugins;
- Kubernetes/Nomad/Swarm workload models inside the APK or Host API;
- CRDT state engines such as Loro for cluster desired state;
- P2Panda as a core management protocol;
- Zenoh as a mandatory overlay, scheduler, database, or application data plane;
- custom OpenTofu provider before real provider-owned resources;
- custom container runtime, VPN, scheduler, consensus system, or distributed filesystem;
- web controller direct-to-phone keys or tunnels;
- community account/DDNS services before identity, abuse, privacy, export, and migration requirements exist;
- USB AOA networking until every base gate is green.

## Explicit library decisions for later Rust work

These decisions apply when the Rust/Slint/controller or Linux-host tasks activate:

| Concern | Default | Boundary |
|---|---|---|
| Async runtime | Tokio | One bounded runtime per daemon; minimize features on constrained targets. |
| HTTP server | Axum | Controller/web endpoints only; use platform-native local IPC on Android/Linux. |
| RPC | Protobuf/Tonic only where typed remote RPC is justified | Do not add alongside HTTP without a concrete use case. |
| Instrumentation | `tracing` | Export through Android logs, bounded local diagnostics, and optional OpenTelemetry. |
| YAML | Parse at controller/import boundaries only | Nodes should consume canonical signed data and native upstream files. |
| Schema tooling | CUE/build-time composition plus upstream schemas | Schemars may document Rust-owned leaf types but is not the public source of truth. |
| Wasm | Optional diagnostic/microsandbox feature | No second workload scheduler or required application format. |
| CRDT | None by default | Consider only for collaborative non-authoritative UI documents. |

## Dependency proposal checklist

Every new dependency proposal must answer:

1. What present capability or evidence gap does it solve?
2. Which module/adapter owns it, and what types are forbidden from leaking inward?
3. Which mature alternatives and standard tools were evaluated?
4. What are its license and distribution implications?
5. How active and responsive is its maintenance?
6. What is the Android/Linux/WSL footprint and supported architecture matrix?
7. How is it pinned, updated, audited, and reproduced?
8. What failure modes and privileged capabilities does it add?
9. What tests prove it on the target platform?
10. What is the removal or migration path?

Agent convenience and code-generation speed are not sufficient reasons to add a dependency.
