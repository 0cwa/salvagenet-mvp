# Tool radar

## Core

- Kotlin/Android SDK for the Android shell.
- Podroid-derived APK-native QEMU execution contract.
- Project domain/use-case contracts.
- JSON profile/enrollment/API contracts.
- SQLite operation/current-state persistence.

## Adopted

- Jetpack Compose, Hilt, coroutines/StateFlow.
- Room 2.8.x.
- QEMU/TCG, QMP, qemu-img, libslirp.
- official Android-aware libtailscale integration and its pinned Go toolchain.
- Ktor CIO 3.x as first Host API adapter.
- cloud-init NoCloud.
- Headscale 0.28.x laboratory and first coordination provider.
- OpenSSH and Ansible at the guest boundary.

## Evaluate behind existing ports

- rustls/axum API sidecar if Ktor TLS/client auth fails.
- direct SQLite instead of Room.
- AVF as an additional VM backend.
- Ignition for immutable guest profiles.
- Nebula as second mesh provider.
- OCI/ORAS artifact transport.
- Slint controller and optional later mobile controller.

## Hold

- multiple active VMs;
- generic third-party profile marketplace;
- dynamic native plugins;
- Kubernetes/Nomad/Swarm models inside the APK;
- web controller direct-to-phone networking;
- Device Owner and patched Android;
- TUF until public remote update distribution;
- USB AOA networking until MVP+.
