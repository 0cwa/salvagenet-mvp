# H02A — Canonical Ubuntu guest boot qualification

## Status

**PLANNED — phase-start review complete.** Activate implementation only from `main` after the post-F01 phase-boundary update merges.

## Outcome

Prove the canonical Ubuntu profile, pinned artifacts, rendered NoCloud input, UEFI/QMP boot, and key-only loopback SSH as one repeatable Linux host-QEMU flow before adding guest mesh behavior or returning to physical Android validation.

## Phase-start review

- F01 merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910`; the checked-in profile JSON and strict manifest contract are now production truth.
- The existing `make qemu-lab-e2e` baseline already separates UEFI/NoCloud/SSH failures from Android packaging, but it must prove that its inputs correspond to the canonical packaged Ubuntu profile rather than a parallel handwritten configuration.
- Guest boot and guest mesh are separate failure domains. Headscale, Tailscale enrollment, tailnet SSH, and coordination outage/recovery are explicitly deferred to H02B.
- Emulator and physical-device behavior are out of scope; host-QEMU evidence cannot close Android gates.
- The task may update only its packet, the host-QEMU laboratory, guest-side qualification tests, its experiment record, and the Makefile entry points needed to expose the reviewed flow.

## Acceptance criteria

- One command performs bounded preflight, preparation, boot, verification, evidence capture, and cleanup.
- The run records the exact source commit and canonical `ubuntu-2404-arm64-uefi` profile bytes or digest used by F01 packaging.
- Ubuntu cloud image, AAVMF code, and AAVMF vars identities are recorded by digest and size before QEMU starts.
- QEMU boots the canonical UEFI/SLIRP profile and a real QMP monitor reports `running`.
- NoCloud completes using the canonical rendered Ubuntu vendor-data asset and produces no unresolved template markers.
- Key-only loopback SSH succeeds before any mesh-specific work begins; password authentication remains disabled.
- A clean guest reboot and a complete QEMU stop/start both return to QMP-running and key-only SSH readiness without replaying one-use bootstrap material.
- The guest disk, cloud-init state, journal/logs, process environment, and temporary metadata are inspected for retained one-use auth keys or callback capabilities; the result is machine-readable and redacted.
- Evidence is bounded under `.local/qemu-lab/`, names its evidence class as `host-qemu`, and states `androidHardwareValidated: false` and `physicalGateEligible: false`.
- Existing repository, profile, guest, Android, and package checks remain green.
- No Headscale/Tailscale guest enrollment, emulator work, qcow2 semantic change, native build rewrite, or physical gate claim is introduced.

## Required checks

```sh
make validate
make test-guest
make qemu-lab-e2e
python3 tools/agents/verify-scope.py H02A
```

The phase-end record must include the host prerequisites, artifact/profile identities, exact command result, evidence path, and any unavailable acceleration or firmware checks. The normal GitHub static and Android/package workflow must remain green even though host-QEMU execution is separate evidence.

## Phase-end verification

1. Check every acceptance criterion against the actual host-QEMU evidence, not only script/unit tests.
2. Confirm the lab consumes canonical F01 profile and guest-init inputs and does not maintain a second profile definition.
3. Confirm loopback SSH succeeds independently before any H02B mesh work is activated.
4. Inspect the secret-residue report and verify redaction before preserving evidence.
5. Run the required checks and complete applicable CI.
6. Record implemented, tested, merge-ready, merged, and host-qualified states separately.
7. Re-evaluate H02B and H03 from the result; activate neither automatically.

## Handoff

Report the exact source commit, host/tool versions, canonical profile and artifact identities, QMP/NoCloud/SSH/restart results, secret-residue findings, cleanup result, evidence classification, and every unmet criterion. Do not claim Android behavior or activate guest mesh work unless H02A passes and the next phase-start review approves it.
