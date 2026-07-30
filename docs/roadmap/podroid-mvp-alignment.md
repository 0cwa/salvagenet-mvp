# Podroid-fork MVP alignment

## Purpose

This document restates the Podroid-fork MVP direction captured in `GOAL.md` and explains where the current implementation has refined that direction. It is a drift check, not a second product specification.

`GOAL.md` remains authoritative for the base MVP. Accepted ADRs may refine implementation choices without silently weakening its success conditions.

## Original MVP direction and current mapping

| Original direction | Current implementation truth | Alignment |
|---|---|---|
| Preserve Podroid's direct APK-native QEMU process model. | The pinned Podroid subtree, external composition hook, executable-in-`nativeLibraryDir` launch, launcher lifetime behaviour, dedicated spawn/reap thread, Unix sockets, QMP, and diagnostic knowledge are retained and tested. | Preserved. |
| Embed private host management and give the Linux guest its own private-network identity. | The Android host uses an Android-aware libtailscale adapter; the guest uses an ordinary Linux Tailscale client. Host and guest enrol separately against Headscale. | Refined into separate identities so a broken guest cannot remove recovery. |
| Remove Alpine as a product dependency and support other ARM64 QEMU guests. | Alpine remains only the known-good direct-kernel qualification oracle. Ubuntu ARM64 UEFI proves the generic cloud-image path; `k3s-worker-lab` checks prerequisites without joining a cluster. | Preserved and made profile-driven. |
| Import configuration that authorises the controller, host mesh, guest access, and provisioning. | Versioned JSON enrolment carries host registration, controller trust/capability data, guest SSH trust, and profile/artifact defaults. Guest mesh redemption is short-lived and separate from host/controller credentials. | Preserved with narrower secret boundaries. |
| Deploy and manage a VM remotely. | Artifact import/upload and VM lifecycle use the typed authenticated Host API. Ordinary SSH is reserved for guest provisioning and troubleshooting. | API chosen over a host shell; this is a deliberate safety improvement. |
| Keep a recovery route when guest networking fails. | QEMU exposes guest SSH only on host loopback; an authenticated Host API tunnel presents it through an OpenSSH `ProxyCommand`. | Preserved. |
| Add optional USB networking only after the core MVP works. | AOA, `node-linkd`, a QEMU stream NIC, TAP/NAT, and SLIRP fallback remain MVP+ and are mechanically blocked until B01–B20 pass. | Preserved. |
| Keep the MVP small and adaptable. | One active VM, qualified ARM64 profiles, a modular monolith, ports/adapters, desired-state reconciliation, and a durable operation journal remain the base limits. | Preserved. |

## Deliberate refinements since the original recommendation

### Typed Host API instead of remote host SSH

The controller does not receive an arbitrary shell on Android. Image delivery, desired generations, lifecycle operations, diagnostics, revocation, and recovery are bounded API resources. OpenSSH remains the standard interface inside the guest.

This is a better direction because it preserves normal Linux tooling without turning Android into a general remote execution surface.

### Canonical profiles and artifact manifests

Checked-in profile JSON, the packaged profile index, guest-init assets, and strict active artifact manifests are now production inputs shared by Android, tests, and laboratories.

This is additional development discipline, not product-scope expansion. It prevents a host-QEMU test from proving a configuration different from the APK.

### Agent-safe physical validation

The current device-lab safety work adds a serial-specific lease, expiring scenario authorisation, diagnostic versus candidate evidence, clean-tree promotion rules, exact artifact/input records, bounded context, and reliable cleanup.

These controls are aligned with the original one-phone test path. They let supervised agents help with destructive or stateful device operations while keeping a human-visible authorization boundary. They do not replace physical evidence, create a device farm, or change Android product behaviour.

### Bounded host-QEMU preflight before guest mesh and phone validation

H02A qualifies the Ubuntu UEFI, QMP, NoCloud, key-only loopback SSH, restart, and secret-hygiene path independently of guest mesh. H02B remains a separate queued guest-mesh qualification. Physical Android evidence remains authoritative.

This split is retained only while it reduces ambiguity. It must not become an open-ended substitute for the one-phone vertical slice.

### Controller upload plus hardened public import

The Host API has two artifact paths:

- authenticated resumable upload from a trusted controller;
- bounded public HTTPS import with enrolled-origin and SSRF protections.

Both publish through the same manifest contract. This refines remote deployment without changing the VM lifecycle boundary.

### Qualified images instead of arbitrary hostile images

The MVP may deploy more than Alpine, but it does not promise arbitrary untrusted images while QEMU shares the application UID. Generic image support means project-qualified ARM64 boot/profile contracts, not unrestricted ISO, host path, kernel argument, or QEMU argument input.

Broader `existing-disk` support requires stronger runtime isolation and an explicit threat model.

### Temporary capability authentication and Python controller

The MVP currently uses an imported high-entropy controller capability over a tailnet-restricted, device-pinned HTTPS endpoint and a Python `phonectl` test client.

These are replaceable adapters. Reviewed mTLS/principal authorisation and a Rust/Slint controller remain later work. They must not change Host API resource shapes merely to justify a rewrite.

### Kotlin/Compose Android shell, Slint later

Kotlin, Compose, Hilt, Room, Ktor, and the Android-aware Tailscale integration are practical MVP implementations. The permanent domain, API, profile, and operation contracts remain independent so a later Slint/Rust controller or host service can reuse the protocol without forcing an Android rewrite before physical semantics settle.

### Evidence-gated guest classes and image sources

A future distinction between guest class, immutable image identity, image source, and distro-family bootstrap adapter is aligned with the original requirement to support non-Alpine images. It is not base-MVP implementation work.

It should begin only after the current Ubuntu contract and physical path are evidenced and a second concrete family demonstrates the abstraction. OCI initially belongs on the controller/image-distribution side, not as arbitrary container-to-VM conversion in the Android app.

## Current critical path

The base MVP remains:

1. finish bounded H02A guest-boot qualification;
2. decide at the phase boundary whether H02B still removes the next highest-value uncertainty;
3. run the existing one-phone HIL sequence for APK-native QEMU, host mesh/API, remote Ubuntu deployment, guest mesh/SSH, recovery, lifecycle, reboot, and controller-offline behaviour;
4. bind every B01–B20 result to one exact source commit and APK;
5. start USB work only after all base gates pass.

Roadmap tooling and the public website may proceed only through explicitly authorised, path-bounded tasks. Agent-safe device-lab preparation may merge when it remains non-overlapping and evidence-neutral, but it does not replace H02A or the physical critical path.

## Drift alarms

A phase or issue requires explicit realignment review if it would:

- replace the Podroid APK-native QEMU path before physical evidence proves a better backend;
- move workload orchestration into the Android Host API;
- expose raw shell, QMP, QEMU arguments, kernel arguments, or host paths;
- make the controller a runtime lease required for an already-running VM;
- combine host and guest network identity so guest failure removes recovery;
- promise arbitrary images before QEMU isolation is addressed;
- start multiple-VM, broad distro, polished controller, OCI-in-APK, AVF, Device Owner, or USB implementation while a base gate is red without a reviewed blocking reason;
- let website status, issue closure, host-QEMU evidence, emulator evidence, or code review stand in for required physical evidence;
- let test authorization or a device lease become a production runtime requirement;
- preserve alpha compatibility code without a real deployed population, support window, tests, and deletion trigger.

## Review rule

At every phase boundary, compare the proposed issue/task graph with this document, `GOAL.md`, the acceptance ledger, and current evidence. Record whether changes are:

- implementation refinements that preserve the MVP;
- evidence-driven reorderings;
- deliberate post-MVP deferrals;
- or actual product-direction changes requiring an ADR and user review.
