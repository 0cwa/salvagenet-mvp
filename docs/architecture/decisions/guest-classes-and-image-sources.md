# ADR: Separate guest classes, image identities, sources, and distro adapters

- Status: accepted direction; implementation gated by evidence
- Scope: post-H02A VM image/runtime product contract

## Context

SalvageNet currently proves two intentionally different guest layouts:

- the Podroid-derived Alpine qualification path uses direct kernel/initramfs boot, a read-only SquashFS root, and separate writable storage;
- the generic Ubuntu path uses UEFI, a qcow2 cloud disk, virtio, NoCloud, OpenSSH, and the truthful `copied-writable` system-disk policy.

These layouts preserve different advantages. They should become supported runtime classes where useful, not a universal Alpine-shaped guest contract and not separate QEMU backends for every distribution.

OCI registries standardize manifests and content-addressed blob distribution. They do not make an ordinary application-container image a bootable QEMU machine image, nor do they standardize every private-registry credential acquisition flow. SalvageNet also needs typed configuration, immutable desired state, local/offline ownership, and a narrow Android attack surface.

## Decision

Keep four concepts independent:

1. **Guest class** defines the supported boot, initialization, health, and storage contract.
2. **Image identity** is an immutable artifact ID, digest, exact size, and supported media/format facts.
3. **Image source** obtains that identity through OCI, authenticated upload, public HTTPS, local file, or offline cache.
4. **Guest-family adapter** implements package, service-manager, SSH, mesh, readiness, and secret-erasure differences without redefining virtual hardware.

Initial user-facing guest classes are:

- `cloud-machine/v1`: UEFI, virtio, bootable cloud disk, NoCloud/cloud-init-like initialization; the default general-purpose self-hosting class.
- `immutable-appliance/v1`: direct kernel/initramfs, read-only system root, explicit persistent data; the eventual user-selectable home for the useful Alpine/Podroid appliance layout.
- `declarative-machine/v1`: externally built declarative guests such as NixOS, activated through a dedicated declarative contract rather than distro package-manager scripts.
- `existing-disk/v1`: an advanced qualified bring-your-own bootable ARM64 disk class; experimental until stronger QEMU process/UID isolation exists.

Future users may choose guest class, immutable image or signed update channel, storage policy, resources, power policy, network profile, and update/rollback policy. They do not choose raw QEMU/kernel arguments, virtio topology, bootloader wiring, arbitrary host paths, or untyped guest scripts.

OCI support first distributes already normalized bootable VM artifacts, firmware, kernels, initramfs images, or SalvageNet artifact bundles. Converting an arbitrary OCI application-container root filesystem into a bootable guest belongs in a controller/image-builder pipeline, not the Android node.

## Rationale

- Preserves Podroid's measured Android/QEMU adaptations without universalizing Alpine-specific guest layout assumptions.
- Avoids a combinatorial `ubuntu-qemu`, `fedora-qemu`, `suse-qemu`, and `arch-qemu` backend matrix.
- Lets one immutable image identity arrive through multiple source providers without changing runtime consumption.
- Keeps mutable tags/channels outside desired state; controllers resolve them to digests before deployment.
- Prevents public APIs from becoming invalid low-level combination generators.
- Keeps hostile arbitrary-image claims blocked by the current same-UID QEMU limitation.

## Consequences

- Desired VM state eventually separates the concrete system-image identity from the guest class/profile identity.
- Profiles evolve toward compatibility and guest-class contracts rather than hard-coding one distribution artifact.
- Guest-family adapters require qualification for bootstrap-secret redemption, key-only SSH, guest identity, mesh installation, readiness, cleanup, restart, and reboot continuity.
- OCI/private-registry support is implemented behind replaceable artifact-source adapters; cloud-provider login workflows do not become domain contracts.
- Storage policy names must remain truthful, including `copied-writable`, future real backing overlays, and immutable-root-plus-data modes.

## Implementation triggers

Begin image-binding/guest-class API work only after:

1. H02A qualifies the current Ubuntu UEFI/NoCloud/QMP/SSH/restart contract with exact artifact evidence;
2. the corresponding path is exercised on a physical Android candidate before claiming device support;
3. the device-lab lease, authorization, candidate-evidence, and exact-input safeguards are merged;
4. one concrete second family or immutable-appliance use case demonstrates the abstraction;
5. API/schema reset, rollback, and retained-artifact behavior are assigned to an active task.

Controller-side OCI resolution should precede Android-native OCI pulling. Add Android OCI pulling only when controller-optional or offline provisioning provides a demonstrated product need. Remote executable profile bundles and hostile arbitrary images remain separate security/trust decisions.
