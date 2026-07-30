# Guest classes and image-source roadmap

This roadmap implements the accepted guest/image ADR in evidence-driven steps. It is not active work authorization; `agents/task-dag.json` controls implementation.

## Phase A — prove the current generic machine contract

- Complete F02 HIL readiness.
- Qualify Ubuntu ARM64 UEFI, virtio, NoCloud, key-only SSH, restart, and secret hygiene on host-QEMU and physical Android.
- Record exact profile version and artifact digests.
- Resolve or honestly rename the copied-writable `qcow2-overlay` behavior.

Exit: one generic cloud-machine contract is proven without relying on Alpine's direct-kernel layout.

## Phase B — separate image binding from guest class

- Add immutable `systemImage` identity to desired VM state and persistence.
- Keep the profile/guest class responsible for compatibility, boot, initialization, health, and requirements.
- Define generation, reset, rollback, and retained-artifact semantics.
- Preserve one-VM and typed-QEMU boundaries.

Exit: a compatible image can be selected independently of the guest class without raw host configuration.

## Phase C — controller-side source providers

- Resolve OCI/ORAS references, GitHub releases, direct HTTPS artifacts, local files, and offline cache entries to immutable digest/size identities.
- Normalize only when needed into supported bootable artifacts.
- Upload through the existing authenticated resumable API.
- Keep registry/cloud authentication in replaceable controller adapters.

Exit: registry diversity does not expand the Android node's public command surface.

## Phase D — qualify representative guest families

Qualify structural representatives rather than every distro at once:

1. Debian/Ubuntu family on `cloud-machine/v1`.
2. Fedora/RHEL family on `cloud-machine/v1`.
3. Alpine on both `cloud-machine/v1` where viable and `immutable-appliance/v1`.
4. NixOS on `declarative-machine/v1`.
5. openSUSE and Arch through the established family-adapter interfaces.

Each adapter proves bootstrap-secret redemption, SSH policy, mesh installation, readiness callback, cleanup, reboot continuity, and native package/service behavior.

## Phase E — bounded Android OCI artifact source

Only when controller-optional or offline local provisioning requires it:

- accept structured registry/repository/digest references;
- support allowlisted SalvageNet VM artifact media types and ARM64 platform selection;
- verify descriptor size/digest and stream into the existing artifact store;
- store credentials through the enrollment/Keystore boundary;
- retain SSRF separation from public HTTPS import;
- reject scripts, raw argv, host paths, and arbitrary container-to-VM conversion.

## Phase F — advanced and security-gated capabilities

- signed channels, rollback, retention, and delegated trust;
- isolated QEMU process/UID or engine boundary;
- qualified `existing-disk/v1` and hostile-image claims;
- optional image factory for container rootfs to bootable appliance conversion;
- measured power/thermal/resource admission and user-facing adaptive policies.

## Explicit non-goals before the base MVP seal

- broad distro matrix;
- arbitrary OCI application container boot;
- remote executable profile bundles;
- direct cloud-provider identity integrations in the APK;
- multiple active VMs;
- USB/AOA networking.
