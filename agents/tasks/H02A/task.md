# H02A — Canonical Ubuntu guest boot qualification

## Status

**ACTIVE — runtime implementation in review; real host evidence pending.** H02A is the sole authorised task in phase `guest-boot-2`. GUEST-01 is live roadmap issue #37; issue state does not replace this task authorization.

## Outcome

Prove the canonical Ubuntu profile, rendered vendor-data, selected artifact identities, UEFI/QMP boot, NoCloud completion, and key-only loopback SSH as one repeatable Linux host-QEMU flow before adding guest mesh behavior or returning to physical Android validation.

## Phase-start review

- WEB04 and its reviewed snapshots are merged; the committed live index has GUEST-01 as the sole active, task-authorized item with no reported roadmap disagreement or fallback.
- Draft PR #20 remains a path-disjoint HIL safety review. It is not a prerequisite, is not authorized by this phase, and supplies no physical evidence.
- F01 remains production truth for packaged profile JSON, rendered guest-init assets, and strict active artifact manifests.
- The production-aligned H02A preparation slice merged through PR #80 at `096ad60136bef2e007ab7a78bb66c16487a41000`; exact-head workflow `30600697377` passed repository, guest, Android, packaging, signature, and alignment checks.
- Preparation consumes the immutable Ubuntu 24.04 ARM64 release dated `20260725`, verifies its exact size and SHA-256, renders canonical vendor-data, creates an independent copied-writable system disk, records matched AAVMF inputs, and launches only the preflight-recorded QEMU command.
- The runtime branch must prove three complete stages: initial boot, clean guest reboot, and complete QEMU stop/start. Each stage requires independent QMP, NoCloud, SSH, host-key, guest-tool, scan, and log records.
- H02A must not create `/var/lib/nodehost/bootstrap.env`, redeem a one-use guest secret, install/enroll Tailscale, or exercise readiness callbacks. Actual redemption, erasure, and guest-mesh persistence checks belong to H02B.
- Host AAVMF evidence records host package paths and identities only. It must not claim byte identity with a separately qualified Android artifact unless that identity is explicitly established.
- Emulator and physical-device behavior are out of scope; host-QEMU evidence cannot close Android gates.
- Runtime ownership, Android process-death recovery, QMP peer authentication, AVF, controller replacement, website implementation, native-runtime rebuilds, and USB remain outside this phase.

## Compatibility policy

None. H02A is pre-release host-QEMU qualification and may make clean-break changes to laboratory inputs. Do not add migration, fallback, dual-read, legacy parsing, or compatibility paths without identifying real deployed state, explaining why reset is unacceptable, isolating compatibility code from canonical production paths, and naming a deletion trigger.

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
- Cleanup stops only the process proven to be the recorded H02A QEMU instance and removes generated seed, key, socket, PID, disk, firmware-copy, and temporary files while retaining only reviewed evidence and the reverified pinned base image.
- Existing repository, profile, guest, Android, and package checks remain green.
- No Headscale/Tailscale guest enrollment, emulator work, qcow2 product-semantic change, native build rewrite, runtime-ownership refactor, or physical gate claim is introduced.

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
4. Inspect the bounded forbidden-material scan, exact scanned paths, and redacted logs before preserving evidence.
5. Confirm three distinct boot IDs and one stable SSH host key across both restart paths.
6. Confirm normal runs consume an existing pinned Ubuntu lock rather than mutating it.
7. Confirm cleanup signals no process unless its `/proc` identity matches the recorded H02A QEMU plan.
8. Run required checks and complete applicable CI.
9. Record implemented, tested, merge-ready, merged, and host-qualified states separately.
10. Re-evaluate H02B, H03, physical validation, and any runtime-ownership investigation from the result; activate none automatically.

## Handoff

Report the exact source commit, host/tool versions, canonical profile/vendor-data identity, Ubuntu lock, AAVMF identities, QMP/NoCloud/SSH/restart results, SSH host-key continuity, forbidden-material scan, cleanup result, evidence classification, and every unmet criterion. Do not claim Android behavior, one-use secret erasure, guest mesh viability, or process-death recovery.
