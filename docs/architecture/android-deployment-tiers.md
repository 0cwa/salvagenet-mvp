# Android deployment and reliability tiers

## Purpose

SalvageNet should support several Android deployment forms without making a custom build, Device Owner enrollment, root, or system patching a prerequisite for the ordinary user.

Each tier publishes explicit capabilities and reliability guarantees. A stronger tier adds platform integration; it does not silently change cluster configuration semantics or require separate workload formats.

## Tier A0 — ordinary stock APK

The user installs the same public APK and imports a runtime provisioning capsule.

Characteristics:

- broadest old-device reach;
- user grants VPN, notification, storage, and battery-policy permissions;
- foreground-service and first-unlock constraints apply;
- QEMU/TCG is the universal first runtime;
- AVF may be selected where separately qualified;
- app update and OEM lifecycle behavior require device evidence;
- no build-time cluster dependency.

This is the primary product path and the current physical milestone.

## Tier A1 — managed stock Android

A Device Owner, enterprise mobility controller, or dedicated-device enrollment may configure permitted Android policies without changing the OS image.

Potential improvements:

- pregrant or guide supported permissions;
- battery/background policy management where Android allows it;
- kiosk/dedicated-device operation;
- controlled app installation and update channels;
- network and certificate policy;
- managed configuration values;
- clearer unattended reboot behavior on qualified devices.

The implementation must use documented platform APIs and publish per-policy evidence. Device Owner is not equivalent to root and cannot be assumed to bypass all OEM lifecycle restrictions.

## Tier A2 — whitelisted or preconfigured APK build

Organizations or communities may build a variant that narrows initial trust and setup choices while retaining the same application architecture and runtime capsule.

Build-time configuration may include:

- allowed authority root public keys;
- permitted controller or enrollment domains;
- default Headscale/Tailscale control URL policy;
- allowed runtime/profile channels;
- update-channel and signing policy;
- organization/community name and restrained branding;
- whether open user-added authorities are allowed;
- optional preinstalled system-app/signature permission declarations when the OS build supports them.

Build-time configuration must not include:

- permanent Tailscale/Headscale pre-authentication keys;
- Swarm/K3s/Nomad join tokens;
- controller private keys;
- user credentials;
- permanent community administrator secrets;
- device-specific identity that should be generated in Android Keystore.

A whitelisted build is a low-priority deployment convenience, not the primary way to select a cluster. Normal cluster attachment remains runtime data in a signed capsule, so changing clusters does not require rebuilding the APK.

## Tier B — AVB-patched Android system backend

`my-avbroot-setup` may inject:

- the same or a compatible preinstalled APK;
- a narrow init daemon;
- SELinux policy and file contexts;
- native runtime/network helpers;
- allowed authority roots and signed build manifest;
- update/rollback integration.

Potential improvements:

- boot-persistent service independent of application UI lifetime;
- native cgroups/namespaces/container access;
- efficient networking and storage integration;
- stronger process/credential separation;
- pre-unlock or unattended behavior where explicitly designed and evidenced;
- native USB networking where supported.

This tier must not expose a general-purpose root shell. The APK authenticates to a structured Binder/AIDL or equivalent system API.

## Build and runtime configuration split

Use this rule:

```text
build configuration
  defines which authorities, channels, platform capabilities, and policy ranges are allowed

runtime capsule
  selects a concrete controller, runtime/profile, overlay attachment, orchestrator attachment, and host policy
```

Build configuration constrains runtime intent; it does not replace it.

## Trust evidence

All tiers generate a device key in Android Keystore where available. Evidence may include:

- APK package and signing certificate;
- hardware/software key security level;
- Verified Boot root key, state, hash, and lock status;
- signed SalvageNet/my-avbroot build manifest;
- Device Owner/managed-policy facts;
- current APK and backend versions.

Android evidence uses the platform-wide canonical boot-trust classes from `platform-strategy.md`:

```text
hardware-vendor-verified-locked
hardware-custom-key-verified-locked
hardware-custom-unlocked-measured
software-measured
unattested
```

Deployment tier is reported separately:

```text
deploymentTier: ordinary-stock | managed-stock | whitelisted-stock | avb-patched
bootTrustClass: hardware-vendor-verified-locked | hardware-custom-key-verified-locked | hardware-custom-unlocked-measured | software-measured | unattested
```

The mapping is explicit:

- ordinary, managed, and whitelisted stock Android normally map to `hardware-vendor-verified-locked` when hardware evidence proves the vendor boot chain is locked and verified;
- an AVB-patched build locked to a recognized custom key maps to `hardware-custom-key-verified-locked`;
- a known custom build with an unlocked bootloader maps to `hardware-custom-unlocked-measured` when measurements are available;
- software-only measurement maps to `software-measured`;
- missing or unusable evidence maps to `unattested`.

Managed policy or a whitelisted APK does not independently raise the boot-trust class. Those facts remain separate inputs to admission policy. Class names describe evidence, not moral trust or workload authorization; admission remains configurable by the cluster/community authority.

## Configuration precedence

Most restrictive valid policy wins:

1. cryptographically protected system/build policy;
2. managed-device policy;
3. signed provisioning capsule;
4. local user preference where allowed.

A lower layer cannot broaden an authority, endpoint, runtime, or update channel forbidden by a higher layer. Conflicts must fail visibly rather than silently choosing a permissive value.

## Updates and recovery

Each tier must document:

- APK update source/signing identity;
- system/ROM update source where applicable;
- capsule/profile/runtime update channels;
- rollback and data continuity;
- authority rotation and revocation;
- safe-mode/recovery access;
- removal consequences;
- which behavior survives reboot before and after first unlock.

## Roadmap relationship

- Current stock APK proof: B01–B20 and DEVICE issues.
- Minimum stock unattended floor: MVP-05.
- Managed/Device Owner and reliability packaging: existing PLAT-11.
- Patched system backend: PLAT-17.
- Attestation trust tiers: PLAT-18.
- Community/account enrollment: COMM-01.

No deployment tier becomes active work unless its task appears in `agents/task-dag.json`.
