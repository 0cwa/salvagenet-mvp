# ADR: Guest classes, image sources, and user choices

- Status: accepted direction; implementation deferred by triggers below
- Decision owners: SalvageNet architecture
- Scope: VM image/runtime product contract after base boot evidence

## Context

The Podroid-derived Alpine qualification path uses direct kernel/initramfs boot, a read-only SquashFS root, and separate writable storage. The generic Ubuntu path uses UEFI, a qcow2 cloud disk, virtio, NoCloud, and SSH. These are useful distinct runtime classes, not distro-specific QEMU backends and not interchangeable layouts.

OCI registries standardize distribution of manifests and digest-addressed blobs, but a normal application container image is not automatically a bootable QEMU machine image. SalvageNet also needs to preserve local ownership, offline delivery, typed configuration, and a narrow Android attack surface.

## Decision

Separate four concepts:

1. **Guest class** defines the supported boot/initialization/storage contract.
2. **Image identity** is an immutable artifact ID plus digest and size.
3. **Image source** obtains that identity from OCI, HTTPS, local upload, or offline cache.
4. **Guest-family adapter** implements package/service/bootstrap differences without redefining virtual hardware.

Initial guest classes:

- `cloud-machine/v1`: UEFI, virtio, cloud disk, NoCloud/cloud-init-like bootstrap; default general-purpose class.
- `immutable-appliance/v1`: direct kernel/initramfs, read-only root, explicit persistent data; preserves useful Alpine/Podroid efficiency as an optional appliance class.
- `declarative-machine/v1`: externally built declarative guest such as NixOS, with configuration activation rather than package-manager scripting.
- `existing-disk/v1`: advanced qualified bring-your-own bootable ARM64 disk; experimental until runtime isolation improves.

User-selectable fields eventually include guest class, image/channel, storage policy, resources, power policy, network profile, and update policy. Internal validated choices include raw QEMU/kernel arguments, virtio topology, bootloader details, disk encoding, package manager, init system, and bootstrap implementation.

OCI support should first distribute SalvageNet VM artifacts or other already normalized bootable artifacts. Container-layer-to-VM construction belongs in a controller/image-builder pipeline, not the Android node.

## Rationale

- Prevents a matrix of distro-specific QEMU backends.
- Preserves Podroid's Android/QEMU adaptations while containing Alpine-specific layout assumptions.
- Lets the same image arrive through OCI, authenticated upload, HTTPS, or offline cache.
- Keeps desired state immutable and reproducible even when users track mutable registry tags or channels.
- Avoids exposing invalid low-level combinations in the public API.
- Keeps hostile arbitrary-image claims blocked until QEMU is isolated from the application UID.

## Consequences

- `profileId` and concrete system-image identity must eventually be separable in desired state.
- Profiles evolve toward compatibility/guest-class contracts rather than one hard-coded distro artifact.
- Guest-family adapters need qualification tests for SSH, identity, readiness, secret erasure, reboot, and mesh behavior.
- OCI/private-registry credentials become replaceable artifact-source adapters; cloud-provider login workflows do not become domain contracts.
- True storage semantics must be named honestly (`backing-overlay`, `copied-writable`, `immutable-root-plus-data`).

## Deferred implementation triggers

Begin the public guest-class/image-binding change only after:

1. Ubuntu UEFI/NoCloud boots on a physical Android candidate with exact artifact evidence;
2. F02 device-lab safeguards are merged;
3. the current profile/artifact resolver has no unresolved production/preflight drift;
4. one concrete second family or immutable appliance use case demonstrates the abstraction;
5. API/schema migration and rollback behavior are assigned to an active packet.

Direct Android OCI pulling may follow controller-side OCI resolution when offline/controller-optional provisioning demonstrates a real need. Arbitrary hostile images require a separate runtime-isolation gate.
