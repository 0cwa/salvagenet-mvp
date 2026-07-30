# Architecture and MVP debt register

This register distinguishes accepted MVP shortcuts from accidental drift. Resolve a large item before the physical vertical slice only when it blocks meaningful evidence, creates a direct security/correctness failure, or makes later evidence test a different configuration from production.

## Open debt

| Priority | Debt | Current consequence | Expiry / next action |
|---|---|---|---|
| P0 | Physical-device evidence is missing | Ten product gates remain `BLOCKED-HARDWARE`; software confidence cannot prove Android/OEM, VpnService, APK-native QEMU, reboot, or controller-offline behavior | Complete F02 device-lab readiness, then run the smallest diagnostic and candidate physical sequences through `tests/hil/`. |
| P0 | Agent-run HIL needs explicit local safety and provenance | Concurrent agents, destructive actions, or dirty worktrees could otherwise produce ambiguous device state or mislabeled evidence | F02 adds a serial lease, expiring authorization, diagnostic/candidate modes, exact input capture, cleanup evidence, and promotion rejection. |
| P1 | Repository-wide GPLv2 release position is not documented | Podroid is GPLv2 and the APK links SalvageNet modules; an APK release without a declared compatible license, notices, corresponding source, and modification records creates avoidable compliance ambiguity | Before distributing a release APK, complete a licensing review, add the repository-level license/notice policy, and verify the published source exactly corresponds to the binary. |
| P1 | Ubuntu `qcow2-overlay` contract is implemented as a copy-once mutable disk | The base remains digest-verified but is not an immutable backing image | Before advertising overlay semantics, create a true qcow2 backing overlay with packaged `qemu-img`, or rename the contract to copied-writable disk. Do not mix this into guest boot qualification unless the lab demonstrates a direct blocker. |
| P1 | Native Podroid runtime assets are extracted from a pinned upstream APK | Packaging is deterministic but the project does not rebuild every shipped native/runtime input itself | Add source/patch-queue builds for QEMU, libslirp, launcher, kernel, initramfs, and qualification rootfs before a reproducible project-native release claim. |
| P1 | `node-shell` owns too many production responsibilities | Composition, enrollment, artifact policy, API wiring, TLS, guest bootstrap, profile storage, and recovery are difficult to review independently | Extract only after a phase demonstrates a review/debugging blocker. |
| P1 | Tailscale adapter package mixes runtime, LocalAPI, VPN, platform, and persistence | Maintenance and physical debugging can blur policy ownership | Keep one Gradle module until B08/B09 evidence identifies a concrete split need; then reorganize internals without changing the `HostMesh` port. |
| P1 | Device-aware resource admission is thin | A valid request can overcommit RAM, CPU, storage, or thermal budget on an old phone | Add measured admission policy after the first physical device resource profile is recorded. |
| P1 | MVP UI/language choices can be mistaken for the permanent cross-platform north star | Kotlin/Compose/Hilt are effective for the current Android candidate, but future Slint/Rust/shared-controller choices could be precluded by accidental domain coupling | Keep domain/API contracts independent and revisit through explicit ADRs after physical semantics settle. |
| P1 | Guest image, boot class, and distro bootstrap are not yet independent contracts | Imported artifacts remain useful only when a packaged profile names their IDs; future user choices could become invalid combinations | Follow the guest-class ADR and roadmap after the Ubuntu physical boot contract is proven. |
| P2 | Enrollment is two bound imports rather than one user-facing bundle | The security model is sound but setup is less convenient than the product goal | Add a `.nodehost` container that preserves independent typed validation and erasure of its sections after base behavior is stable. |
| P2 | QEMU shares the application UID | Qualified guests are acceptable, hostile arbitrary images are not a strong boundary | Prototype isolated-process or engine-APK file-descriptor brokering before claiming hostile arbitrary-image support. |
| P2 | Controller remains the Python MVP CLI | It is sufficient for validation but not the durable cross-platform product | Replace behind the stable Host API after physical semantics settle. |
| MVP+ | USB/AOA networking | Adds a Linux daemon, custom framing, TAP/NAT, permissions, reconnect, MTU, and a hardware matrix | Keep blocked in the roadmap until every base gate is PASS; do not reserve a root directory meanwhile. |

## Resolved debt

| Resolved item | Evidence |
|---|---|
| Canonical profile and artifact-manifest production path | F01 merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910`; packaged JSON and one manifest contract now drive production. |
| Reproducible Podroid vendoring boundary | PR #8 merged at `778feb4bf286d24774eadbf8a6ea0051c0f7a219`; the pinned subtree, external integration hook, ordered patch series, and verification tooling are authoritative. |
| Bounded private/local artifact delivery | H01 added authenticated resumable upload and merged at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`. |
| Fragmented physical test scripts | `tests/hil/` is the sole physical runner; H04 hardening merged at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. |

## Refactor rule

Before the final base-MVP seal, a refactor is justified only when it directly unblocks a current phase/hardware gate, fixes a demonstrated security/correctness failure, reduces measured debugging ambiguity, makes preflight and production execute the same contract, or replaces an MVP hack whose explicit expiry trigger has occurred.
