# H02 — Host-QEMU and Headscale guest E2E

## Outcome

Turn the existing Ubuntu host-QEMU smoke test into a repeatable laboratory that exercises NoCloud, key-only SSH, one-use guest Headscale enrollment, readiness, restart, and redacted evidence.

## Prerequisites

None; active-cycle base is current `main`.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- One command prepares, boots, verifies, records, and cleans up the host-QEMU lab.
- The exact pinned Ubuntu and UEFI artifacts are recorded by digest.
- The guest joins the disposable Headscale lab with a separate tagged identity and one-use key.
- Ordinary SSH succeeds through the guest tailnet identity and through loopback SLIRP for diagnosis.
- A restart and Headscale interruption/recovery scenario produce machine-readable results.
- Guest disk and cloud-init log inspection finds no retained one-use auth key or callback capability.
- No result is represented as Android or physical-device evidence.

## Required checks

```sh
make validate
make qemu-lab-e2e
make test-guest
```

## Handoff

Report commit SHA(s), exact tests and lab runs, evidence paths, checks unavailable in the current environment, concrete deferred items, and the smallest next blocker.
