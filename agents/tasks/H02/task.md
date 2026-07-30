# H02 — Host-QEMU and Headscale guest E2E

## Status

**QUEUED FOR PHASE-START REVIEW — not active work.**

H02 may be activated only after F01 is merged and its phase-end review confirms that the Linux lab and Android runtime consume equivalent profile and artifact semantics.

## Provisional outcome

Turn the existing Ubuntu host-QEMU smoke test into repeatable guest-path qualification for NoCloud, key-only SSH, one-use guest Headscale enrollment, readiness, restart, and redacted evidence.

## Required phase-start review

Before activation:

1. Inspect the F01 result and prove that the lab inputs correspond to the packaged production profile.
2. Re-run the current QEMU smoke and Headscale lab preflight.
3. Decide whether H02 should remain one task or split into:
   - guest boot/NoCloud/key-only SSH/secret-hygiene qualification; and
   - guest Headscale identity, tailnet SSH, interruption, and recovery qualification.
4. Remove acceptance items already proved by F01 or existing tests.
5. Confirm all required external tools and disposable Headscale inputs can be provisioned without storing live credentials in Git.

## Provisional acceptance criteria

- One command prepares, boots, verifies, records, and cleans up the host-QEMU lab.
- Exact pinned Ubuntu and UEFI artifacts are recorded by digest.
- Key-only SSH succeeds through loopback SLIRP before mesh-specific assertions begin.
- The guest joins the disposable Headscale lab with a separate tagged identity and one-use key.
- Ordinary SSH succeeds through the guest tailnet identity.
- Restart and Headscale interruption/recovery scenarios produce bounded machine-readable results.
- Guest disk and cloud-init log inspection finds no retained one-use auth key or callback capability.
- No result is represented as Android or physical-device evidence.

## Provisional checks

```sh
make validate
make qemu-lab-e2e
make test-guest
python3 tools/agents/verify-scope.py H02
```

## Handoff

Do not begin from this packet as written. At the next phase boundary, revise its scope, dependencies, allowed paths, acceptance criteria, and evidence expectations before changing implementation files.
