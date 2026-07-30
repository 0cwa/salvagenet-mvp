# Architecture and MVP debt register

This register distinguishes accepted MVP shortcuts from accidental drift. Resolve a large item before the physical vertical slice only when it blocks meaningful evidence, creates a direct security/correctness failure, or makes later evidence test a different configuration from production.

## Open debt

| Priority | Debt | Current consequence | Expiry / next action |
|---|---|---|---|
| P0 | Physical-device evidence is missing | Ten product gates remain `BLOCKED-HARDWARE`; software confidence cannot prove Android/OEM, VpnService, APK-native QEMU, reboot, or controller-offline behavior | Merge F01, complete the narrowly scoped guest-boot preflight, then execute the existing HIL vertical slice when hardware is available. Diagnostic device runs may happen earlier, but final evidence must bind one exact candidate commit/APK. |
| P0 | F01 canonical profile/manifest foundation is under review-fix revalidation | The split source of truth is removed, but valid PR #7 findings changed path resolution, traversal validation, manifest listing, large-artifact preparation, and tests after the prior green candidate. `main` is not authoritative until the exact review-fix head passes and merges. | Baseline head `71a04acedd11221fbefe2c0fa43984141ec11ed4` passed Actions run `30543765626`. Complete full revalidation, resolve review threads, merge only the exact tested head, record the merge SHA, and move this item to resolved debt. |
| P1 | Ubuntu `qcow2-overlay` contract is implemented as a copy-once mutable disk | The base remains digest-verified but is not an immutable backing image | Before advertising overlay semantics, create a true qcow2 backing overlay with packaged `qemu-img`, or rename the contract to copied-writable disk. Do not mix this into guest boot qualification unless the lab demonstrates a direct blocker. |
| P1 | Native Podroid runtime assets are extracted from a pinned upstream APK | Packaging is deterministic but the project does not rebuild every shipped native/runtime input itself | Add source/patch-queue builds for QEMU, libslirp, launcher, kernel, initramfs, and qualification rootfs before a reproducible project-native release claim. |
| P1 | `node-shell` owns too many production responsibilities | Composition, enrollment, artifact policy, API wiring, TLS, guest bootstrap, profile storage, and recovery are difficult to review independently | Extract only after a phase demonstrates a review/debugging blocker. F01 introduced narrow profile and manifest adapters without a broad package split. |
| P1 | Tailscale adapter package mixes runtime, LocalAPI, VPN, platform, and persistence | Maintenance and physical debugging can blur policy ownership | Keep one Gradle module until B08/B09 evidence identifies a concrete split need; then reorganize internals without changing the `HostMesh` port. |
| P1 | Device-aware resource admission is thin | A valid request can overcommit RAM, CPU, storage, or thermal budget on an old phone | Add measured admission policy after the first physical device resource profile is recorded. |
| P1 | MVP UI/language choices can be mistaken for the permanent cross-platform north star | Kotlin/Compose/Hilt are effective for the current Android candidate, but future Slint/Rust/shared-controller choices could be precluded by accidental domain coupling | Keep domain/API contracts independent. Revisit through explicit ADRs after physical semantics settle; do not perform a UI or shared-core rewrite during base validation. |
| P2 | Enrollment is two bound imports rather than one user-facing bundle | The security model is sound but setup is less convenient than the product goal | Add a `.nodehost` container that preserves independent typed validation and erasure of its sections after base behavior is stable. |
| P2 | QEMU shares the application UID | Qualified guests are acceptable, hostile arbitrary images are not a strong boundary | Prototype isolated-process or engine-APK file-descriptor brokering post-MVP. |
| P2 | Controller remains the Python MVP CLI | It is sufficient for validation but not the durable cross-platform product | Replace behind the stable Host API after physical semantics settle. |
| MVP+ | USB/AOA networking | Adds a Linux daemon, custom framing, TAP/NAT, permissions, reconnect, MTU, and a hardware matrix | Keep blocked until every base gate is PASS. |

## Resolved debt

| Resolved item | Evidence |
|---|---|
| Bounded private/local artifact delivery | H01 added authenticated resumable upload and merged at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b` without weakening public-import SSRF policy. |
| Complete remote software/package reproduction | GitHub Actions run `30510377089` passed static/contracts, controller, JVM, Android/lint, guest qualification, packaged APK, signature, 16 KiB alignment, and candidate upload for the validated H01 head. |
| Fragmented physical test scripts | `tests/hil/` is the sole physical runner; H04 hardening merged at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. |

## Refactor rule

Before the final base-MVP seal, a refactor is justified only when it:

1. directly unblocks a current phase or hardware gate;
2. fixes a demonstrated security/correctness failure;
3. reduces a measured debugging ambiguity;
4. makes preflight and production execute the same contract; or
5. replaces an MVP hack whose explicit expiry trigger has occurred.
