# H02A — Canonical Ubuntu guest boot qualification

## Status

**ACTIVE — phase-start review complete; implementation not started.** Begin implementation only from current `main` after the post-F01 transition PR merges.

## Outcome

Prove the canonical Ubuntu profile, rendered vendor-data, selected artifact identities, UEFI/QMP boot, NoCloud completion, and key-only loopback SSH as one repeatable Linux host-QEMU flow before adding guest mesh behavior or returning to physical Android validation.

## Phase-start review

- F01 merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910`; packaged profile JSON and strict active manifests are production truth.
- The existing `make qemu-lab-e2e` baseline is not yet sufficient: it writes a parallel cloud-init document and discovers arbitrary host firmware without binding those choices to the canonical profile/evidence record.
- H02A must use the canonical rendered Ubuntu vendor-data as NoCloud vendor-data, while a clearly test-only NoCloud user-data layer provides the ephemeral SSH public key and a mesh-independent readiness marker.
- H02A must not create `/var/lib/nodehost/bootstrap.env`, redeem a one-use guest secret, install/enroll Tailscale, or exercise readiness callbacks. Actual redemption, erasure, and guest-mesh persistence checks belong to H02B.
- The Ubuntu cloud image must become reproducibly pinned in `profiles/locks/images.lock.json`; repeated runs consume the pinned digest instead of silently advancing `current`.
- Host AAVMF firmware may come from the documented package search path, but its exact source path, digest, size, and package/tool facts must be recorded. Host evidence must not claim byte identity with an Android-uploaded AAVMF artifact unless that identity is explicitly established.
- Guest boot and guest mesh are separate failure domains. Headscale, Tailscale enrollment, tailnet SSH, and coordination outage/recovery are deferred to H02B.
- Emulator and physical-device behavior are out of scope; host-QEMU evidence cannot close Android gates.
- The task may update only its packet, the specifically listed host-QEMU laboratory files, H02A-named helpers, guest-side qualification tests, the exact Ubuntu image lock/pinning helper, its experiment record, and Makefile entry points needed to expose the reviewed flow.

## Acceptance criteria

- One command performs bounded preflight, preparation, boot, verification, restart checks, evidence capture, and cleanup.
- The run records the exact source commit and SHA-256 of the canonical `ubuntu-2404-arm64-uefi` profile and rendered Ubuntu vendor-data used by F01 packaging.
- The Ubuntu cloud image is pinned by URL, SHA-256, and size in `profiles/locks/images.lock.json`; a normal lab run verifies and consumes that lock without rewriting it.
- AAVMF code and vars source paths, SHA-256 values, and sizes are recorded before QEMU starts; any difference from a separately qualified Android artifact is stated rather than hidden.
- QEMU arguments are derived from or checked against canonical profile fields for architecture, `virt`, CPU model, TCG, PCI virtio, UEFI, SLIRP, and recovery SSH port rather than maintained as an unexplained parallel profile.
- QEMU boots the canonical UEFI/SLIRP shape and a real QMP monitor reports `running`.
- NoCloud uses the canonical rendered vendor-data plus an explicitly test-only user-data layer. `cloud-init status --wait` completes and no unresolved template markers remain.
- Key-only loopback SSH succeeds; password authentication, keyboard-interactive authentication, and root login are disabled.
- A clean guest reboot and a complete QEMU stop/start both return to QMP-running, cloud-init-complete, and key-only SSH readiness.
- H02A introduces no NodeHost or guest-mesh authentication key, bootstrap token, or callback capability. An ephemeral SSH public key is permitted. A bounded scan of seed inputs, cloud-init state, logs, process environment, and temporary metadata confirms no secret-shaped canary or forbidden bootstrap material is present. One-use redemption/erasure remains explicitly untested until H02B.
- Evidence is bounded under `.local/qemu-lab/`, names its evidence class as `host-qemu`, and states `androidHardwareValidated: false`, `physicalGateEligible: false`, and `guestMeshValidated: false`.
- Cleanup stops QEMU and removes generated seed, key, socket, PID, and temporary files while retaining only the explicitly documented evidence and cached pinned base image.
- Existing repository, profile, guest, Android, and package checks remain green.
- No Headscale/Tailscale guest enrollment, emulator work, qcow2 product-semantic change, native build rewrite, or physical gate claim is introduced.

## Required checks

```sh
make validate
make test-guest
make qemu-lab-e2e
python3 tools/agents/verify-scope.py H02A
```

The phase-end record must include host prerequisites, lock/profile/vendor-data/firmware identities, exact command result, evidence path, and any unavailable acceleration or firmware checks. The normal GitHub static and Android/package workflow must remain green even though host-QEMU execution is separate evidence.

## Phase-end verification

1. Check every acceptance criterion against actual host-QEMU evidence, not only script or unit tests.
2. Confirm the lab consumes canonical F01 profile/vendor-data inputs and does not maintain a second complete profile or cloud-init definition.
3. Confirm loopback SSH succeeds independently without bootstrap secret redemption or guest mesh.
4. Inspect the bounded forbidden-material scan and verify redaction before preserving evidence.
5. Confirm normal runs consume an existing pinned Ubuntu lock rather than mutating it.
6. Run the required checks and complete applicable CI.
7. Record implemented, tested, merge-ready, merged, and host-qualified states separately.
8. Re-evaluate H02B and H03 from the result; activate neither automatically.

## Handoff

Report the exact source commit, host/tool versions, canonical profile/vendor-data identity, Ubuntu lock, AAVMF identities, QMP/NoCloud/SSH/restart results, forbidden-material scan, cleanup result, evidence classification, and every unmet criterion. Do not claim Android behavior, one-use secret erasure, or guest mesh viability.
