# Platform and runtime strategy

## Purpose

SalvageNet begins with one Android/QEMU implementation but is intended to enable heterogeneous devices. This document records the platform order, common boundaries, and concrete reasons to defer abstraction until evidence exists.

## Platform order

| Priority | Platform | First execution path | Distinguishing concern |
|---|---|---|---|
| A | Stock old Android | APK-native ARM64 QEMU/TCG; AVF where later qualified | Android lifecycle, foreground service, VPN, Doze, OEM process policy, thermal and storage limits |
| B | Patched Android | AVB-installed daemon plus native Linux/system-container backend | init/SELinux integration, verified boot, root privileges, update/rollback, strong API boundary |
| C | ARM64 SBC | Native Linux service; optional container or VM | Stable power/network/storage, control-plane and gateway eligibility |
| D | Existing Linux | Native service, OCI container, VM, or microsandbox | Packaging diversity, least-privilege mode selection, reuse of existing host tools |
| E | Dedicated Linux appliance | Reproducible minimal OS image | Atomic update/rollback, secure boot, recovery, hardware breadth |
| F | Windows via WSL | Linux service inside WSL plus narrow native setup bridge | WSL lifecycle, networking, persistence, Windows startup and recovery |

This order governs implementation priority, not permanent architecture. A later platform may be prototyped when it resolves a current blocker, but it must not displace physical proof of the higher-priority path without reviewed evidence.

## Common host responsibilities

Every host implementation should provide the parts that are genuinely cross-platform:

- stable node and installation identity;
- capability and trust evidence;
- accepted provisioning-capsule revision;
- one authoritative desired/observed reconciler;
- durable operation lifecycle;
- execution-environment lifecycle and observations;
- data ownership and reset/remove semantics;
- overlay/bootstrap integration;
- upstream attachment lifecycle;
- bounded diagnostics and recovery;
- update, rollback, and revocation behavior.

It should not force identical low-level mechanics. Android foreground services, an init daemon, systemd, WSL, QEMU, crosvm, namespaces, and OCI runtimes remain platform adapters.

## Execution-environment vocabulary

The current public API is VM-shaped because QEMU is the first product backend. Before adding patched Android and native Linux, evolve toward an additive `ExecutionEnvironment` or equivalent resource:

```text
ExecutionEnvironment
├── identity and backend kind
├── desired lifecycle state
├── immutable profile/artifact identity
├── persistent data declarations
├── observed resources and health
├── attachment state
├── recovery endpoints
└── backend-specific capabilities
```

Backend kinds may include:

```text
android-qemu
android-avf
android-system
android-termux       only if later retained and qualified
linux-native
linux-container
linux-vm
linux-microsandbox
wsl
```

Do not implement all names up front. The contract should be revised from QEMU plus the first structurally different backend, with an additive compatibility route for the proven MVP API if users exist by then.

## A. Stock Android APK

### Current backend

Preserve the Podroid-derived APK-native QEMU process model until physical validation is complete:

- executable packaging and launcher lifetime behavior;
- dedicated process spawn/reap path;
- typed QEMU command compilation;
- QMP lifecycle observations;
- qualified ARM64 profiles;
- system/data separation;
- separate host and guest identity;
- host-mediated recovery.

### Reliability tier

The stock tier must publish exactly what it can guarantee:

- whether setup is complete before first unlock;
- foreground-service and notification requirements;
- battery-optimization guidance;
- wake-lock policy;
- screen-off and Doze results;
- OEM/model qualification;
- reboot and app-update behavior;
- thermal and storage stop rules.

No user-facing setting should imply an unkillable background process on arbitrary OEM firmware.

### AVF

AVF is a later alternative backend where the device and build expose the required capability. It must pass the same lifecycle, profile, data, diagnostics, and recovery contracts and be compared with QEMU rather than silently replacing it.

## B. Patched Android with `my-avbroot-setup`

### Delivery

Treat the patch workflow as a build and update provider that can add:

```text
/system/bin/salvagenet-hostd
/system/etc/init/salvagenet-hostd.rc
SELinux policy and file contexts
signature/privileged permission declarations
optional preinstalled APK
signed build manifest and allowed authority roots
native runtime/network helper artifacts
```

The same APK remains separately installable. A patched device discovers and authenticates the system service and gains the higher capability tier.

### Privileged API

Use Binder/AIDL or another narrow authenticated local protocol. Authorize the APK signing identity or assigned UID. Expose structured operations only, such as:

```text
probe capabilities
prepare/start/stop environment
mount verified artifact
configure bounded namespace/network resources
set resource policy
rotate system image slot
return observations and diagnostics
```

Do not expose shell strings, arbitrary paths, arbitrary mount operations, or a generic root command runner.

### Native runtime

The first native backend may use a project-qualified system container or chroot/namespace runtime based on the best maintained foundation available when implementation starts. Reuse cgroups, namespaces, OCI images, containerd/runc, Podman, LXC, or a focused upstream Android runtime rather than writing a new container engine.

The backend is privileged and should be advertised for trusted workloads unless a stronger isolation boundary is separately evidenced.

### Attestation

The APK generates a device key through Android Keystore and requests key attestation where available. The controller may examine:

- challenge freshness;
- key security level;
- APK package/signing identity;
- `verifiedBootKey`;
- `deviceLocked`;
- `verifiedBootState`;
- `verifiedBootHash`;
- OS and patch information;
- signed `my-avbroot-setup` build manifest.

Suggested trust classes:

```text
hardware-vendor-verified
hardware-custom-key-locked
hardware-custom-unlocked-measured
software-measured
unattested
```

An unlocked bootloader remains a lower-assurance class even when the build is known. Policy may still admit it for appropriate workloads.

## C. SBC native host

The SBC implementation should become the reference stable-host adapter:

- Rust or another chosen shared daemon implementation;
- systemd and OpenRC packaging;
- native execution or existing OCI/VM runtime;
- ordinary Linux Tailscale client;
- optional Zenoh router;
- optional artifact/cache service;
- optional Headscale service;
- orchestrator manager eligibility from measured policy;
- later USB `node-linkd` peer.

A stable-cell role may combine several services, but each remains independently replaceable and observable.

## D. Existing Linux

Support several deployment envelopes without creating several products:

1. native package and service;
2. rootless or privileged OCI container where host access is sufficient;
3. VM where isolation or dependency compatibility requires it;
4. bounded WebAssembly/microsandbox only for diagnostics or workloads that naturally fit it.

Mode selection should be capability- and policy-driven. The controller should explain unavailable features rather than silently weakening them.

## E. Dedicated Linux appliance

Build this only after SBC and existing-Linux evidence stabilizes:

- minimal reproducible image;
- immutable or A/B system layer;
- separate durable data;
- signed updates and rollback protection;
- first-boot capsule import;
- standard SSH/recovery route;
- native upstream agents;
- NixOS, Fedora CoreOS/Ignition, or another existing declarative base evaluated before a new build system.

A custom appliance must not require applications to use a SalvageNet package format.

## F. WSL

Reuse the Linux daemon and attachment adapters. The Windows-specific component owns only:

- distribution installation and version checks;
- startup registration;
- Windows/WSL networking discovery;
- controlled file/credential handoff;
- status and recovery when WSL is stopped;
- uninstall and data retention choices.

Do not expose Windows host shell commands through the remote Host API.

## Shared implementation languages and UI

- Keep Kotlin for Android lifecycle/platform integration while it is the most direct maintained option.
- Keep permanent domain and wire contracts language-neutral.
- Use Rust where a shared controller/host implementation materially reduces duplication and has a clear Android/Linux build path.
- Start Slint with the cross-platform controller. Reconsider the Android UI only after physical lifecycle semantics settle; do not make the runtime proof depend on an Android UI rewrite.
- Keep native C/JNI surface minimal and isolated around upstream runtime/platform APIs.

## Capability and reliability classes

Publish facts rather than one opaque score:

```text
runtime backend and acceleration
root/system privilege tier
attestation/trust tier
memory and storage limits
external-power state and policy
thermal state and sustained history
network paths and stability
background/reboot guarantee
manager eligibility
storage eligibility
```

Upstream labels, taints, constraints, and resource reservations should be generated from these facts where the selected orchestrator supports them.

## Refactoring rule

Do not pause current physical validation for a cross-platform rewrite. Broaden a contract before the second backend only when the current public shape would otherwise force a known planned backend to lie. Prefer additive names and adapters over framework migration.
