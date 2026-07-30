# Tool radar

## Core

- Kotlin/Android SDK for the current Android platform shell and lifecycle integration.
- Podroid-derived APK-native QEMU execution contract.
- Project domain/use-case contracts, kept independent of implementation languages and frameworks.
- JSON profile, enrollment, artifact-manifest, and API contracts.
- SQLite operation/current-state persistence semantics.

## Adopted for the current candidate

- Jetpack Compose, Hilt, coroutines/StateFlow.
- Room 2.8.x.
- QEMU/TCG, QMP, qemu-img, libslirp.
- official Android-aware libtailscale integration and its pinned Go toolchain.
- Ktor CIO 3.x as first Host API adapter.
- cloud-init NoCloud.
- Headscale 0.28.x laboratory and first coordination provider.
- OpenSSH and Ansible at the guest boundary.

These choices should not leak into the domain contracts. Adoption for the MVP is not a commitment to use the same language or UI stack for every future platform.

## Evaluate behind existing contracts

- Rust implementation for a durable cross-platform controller and possible shared pure-domain components after physical semantics stabilize.
- Slint controller and later mobile/desktop UI where it demonstrably reduces duplication without taking over Android lifecycle ownership.
- rustls/axum API sidecar if Ktor TLS/client-auth or lifecycle evidence fails.
- direct SQLite instead of Room.
- AVF as an additional VM backend.
- Ignition for immutable guest profiles.
- Nebula as a second mesh provider.
- OCI/ORAS artifact transport.

Do not start a Kotlin-to-Rust, Compose-to-Slint, or controller rewrite during H02A or before the physical vertical slice identifies a concrete benefit. Such a transition requires an ADR and contract-preserving migration plan.

## Hold

- multiple active VMs;
- generic third-party profile marketplace;
- dynamic native plugins;
- Kubernetes/Nomad/Swarm models inside the APK;
- web controller direct-to-phone networking;
- Device Owner and patched Android;
- TUF until public remote update distribution;
- USB AOA networking until MVP+.
