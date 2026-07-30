# Guest classes and image-source roadmap

This roadmap sequences the accepted guest/image ADR. It is not active work authorization; `agents/task-dag.json` remains authoritative and H02A stays the sole active task.

## Phase A — prove the current cloud-machine contract

- Complete H02A against the canonical Ubuntu profile and pinned artifacts on host QEMU.
- Prove UEFI, real QMP running state, NoCloud completion, key-only SSH, stop/start/restart, and retained-secret hygiene.
- Record the exact profile version, image digest, firmware digests, and truthful `copied-writable` storage behavior.
- Re-run the corresponding contract on a physical Android candidate before claiming device support.

Exit: one generic `cloud-machine/v1` contract is evidenced independently of Alpine's direct-kernel layout.

## Phase B — separate image binding from guest class

- Add an immutable `systemImage` identity to desired VM state, API schemas, persistence, and evidence.
- Keep the guest class/profile responsible for compatible boot, initialization, health, hardware requirements, and storage-policy validation.
- Define alpha reset behavior plus generation, replacement, rollback, retained-artifact, and data-preservation semantics.
- Preserve the one-VM limit and typed QEMU boundary.

Exit: a compatible image can be selected independently of its guest class without exposing raw host configuration.

## Phase C — controller-side image-source providers

- Resolve OCI/ORAS references, GitHub releases, direct HTTPS artifacts, local files, and offline cache entries to immutable digest/size identities.
- Normalize inputs into supported bootable artifacts only when necessary.
- Upload through the existing authenticated resumable artifact API.
- Keep registry and cloud-provider authentication in replaceable controller adapters.

Exit: registry diversity does not enlarge the Android Host API or weaken public-import SSRF boundaries.

## Phase D — qualify representative guest families

Qualify structural representatives instead of promising every distribution at once:

1. Debian/Ubuntu family on `cloud-machine/v1`.
2. Fedora/RHEL family on `cloud-machine/v1`.
3. Alpine on `cloud-machine/v1` where viable and `immutable-appliance/v1` where its compact layout is valuable.
4. NixOS on `declarative-machine/v1`.
5. openSUSE and Arch through the established family-adapter interfaces.

Each adapter proves native package/service behavior, bootstrap-secret redemption, key-only SSH, mesh installation, readiness callback, cleanup, restart, and reboot continuity.

## Phase E — bounded Android OCI artifact source

Activate only when controller-optional or offline local provisioning demonstrates the need:

- accept structured registry, repository, digest, artifact type, and ARM64 platform references;
- support an allowlist of SalvageNet VM-artifact media types;
- verify every descriptor size/digest and stream blobs into the existing digest-addressed artifact store;
- store credentials through enrollment and Android Keystore-backed boundaries;
- remain separate from the public HTTPS importer and its SSRF policy;
- reject remote scripts, raw QEMU/kernel arguments, host paths, and arbitrary container-to-VM conversion.

## Phase F — advanced trust and runtime isolation

- signed update channels, retention, rollback, revocation, and delegated trust;
- isolated QEMU process/UID or a separate engine boundary;
- qualified `existing-disk/v1` and hostile-image claims;
- optional controller/image-factory conversion from container rootfs artifacts to bootable appliances;
- measured power, thermal, memory, and storage admission with user-facing adaptive policies.

## Explicit non-goals before the base MVP seal

- a broad distro matrix;
- arbitrary OCI application-container boot;
- remote executable profile bundles;
- cloud-provider identity integrations embedded in the APK;
- multiple active VMs;
- USB/AOA networking.
