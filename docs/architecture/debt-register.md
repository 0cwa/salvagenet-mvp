# Architecture and MVP debt register

This register distinguishes accepted MVP shortcuts from accidental drift. Do not resolve a large item before the physical vertical slice unless it blocks that slice or creates a direct security failure.

| Priority | Debt | Current consequence | Expiry / next action |
|---|---|---|---|
| P0 | Physical-device evidence is missing | Ten product gates remain `BLOCKED-HARDWARE`; software confidence cannot prove Android/OEM behavior | Execute D01–D05 before new feature work. |
| P0 | Private/local artifact delivery has no bounded path | The hardened downloader rejects LAN, loopback, and tailnet targets, so a local controller cannot directly serve a VM image | Add authenticated resumable Host API upload or an enrollment-pinned private origin; never weaken SSRF rules globally. |
| P0 | CI did not reproduce the complete local build | Go/libtailscale, packaging, signature, alignment, and exact artifact evidence were not all exercised remotely | The main CI workflow now pins Go and uploads an exact commit-bound device-lab candidate. Require it before release. |
| P1 | Android production profiles are duplicated in Kotlin and JSON | Adding Debian/new Ubuntu profiles can drift from checked-in profile contracts | After D03, load validated packaged JSON through one production `ProfileRegistry`; Kotlin retains compatibility checks only. |
| P1 | Ubuntu `qcow2-overlay` contract is implemented as a copy-once mutable disk | The base remains digest-verified but is not an immutable backing image | Before advertising overlay semantics, create a true qcow2 backing overlay with packaged `qemu-img`, or rename the profile contract to copied-writable disk. |
| P1 | Native Podroid runtime assets are extracted from a pinned upstream APK | Packaging is deterministic but the project does not rebuild every shipped native/runtime input itself | Add source/patch-queue builds for QEMU, libslirp, launcher, kernel, initramfs, and qualification rootfs before a reproducible release claim. |
| P1 | `node-shell` owns too many production responsibilities | Composition, enrollment, artifact policy, API wiring, TLS, guest bootstrap, and recovery are difficult to review independently | Do not perform a broad pre-device refactor. After D02/D03, extract artifact import/publication and declare all SQL through `node-store` migrations. |
| P1 | Tailscale adapter package mixes runtime, LocalAPI, VPN, platform, and persistence | Maintenance and physical debugging can blur policy ownership | Keep one Gradle module, but move internals into `runtime/`, `localapi/`, `vpn/`, `platform/`, and `persistence/` packages after D02. |
| P1 | Device-aware resource admission is thin | A valid API request can still overcommit RAM, CPU, storage, or thermal budget on an old phone | Add a measured admission policy after the first device resource profile is recorded. |
| P2 | Enrollment is two bound imports rather than one user-facing bundle | The security model is sound but setup is less convenient than the product goal | Add a `.nodehost` container that preserves independent typed validation and erasure of its sections. |
| P2 | QEMU shares the application UID | Qualified guests are acceptable, hostile arbitrary images are not a strong boundary | Prototype isolated-process or engine-APK file-descriptor brokering post-MVP. |
| P2 | Controller remains the Python MVP CLI | It is sufficient for validation but not the durable cross-platform product | Replace behind the stable Host API after physical semantics settle. |
| MVP+ | USB/AOA networking | Adds a Linux daemon, custom framing, TAP/NAT, permissions, reconnect, MTU, and hardware matrix | Keep blocked until every base gate is `PASS`. |

## Refactor rule

A refactor is justified before D07 only when it:

1. directly unblocks a hardware gate;
2. fixes a demonstrated security/correctness failure;
3. reduces a device-debugging ambiguity; or
4. preserves a contract while replacing an MVP hack whose expiry trigger has occurred.
