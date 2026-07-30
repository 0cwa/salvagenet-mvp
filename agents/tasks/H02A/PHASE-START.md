# H02A phase-start findings

This file is a concise implementation handoff, not a replacement for `task.md`.

## Existing baseline

`make qemu-lab-e2e` currently:

1. downloads Ubuntu `current` and writes the digest into the tracked lock during preparation;
2. creates a qcow2 backing overlay;
3. writes parallel `meta-data` and `user-data` with an SSH key and readiness marker;
4. copies whichever AAVMF files the host search discovers;
5. starts QEMU and runs one QMP/SSH smoke;
6. writes a basic evidence report and stops QEMU.

## Required H02A corrections

- Pin Ubuntu explicitly, then make normal runs consume and verify the lock without mutation.
- Render and use the canonical Ubuntu vendor-data as NoCloud vendor-data.
- Keep the SSH key/readiness marker in a clearly test-only user-data file.
- Do not create `bootstrap.env` or activate guest mesh/bootstrap behavior.
- Resolve/check QEMU arguments against canonical profile fields.
- Record source/profile/vendor-data/image/AAVMF/tool identities before boot.
- Add cloud-init completion, SSH policy, guest reboot, full QEMU stop/start, forbidden-material scan, cleanup assertions, and bounded evidence classification.

## Non-goals

Headscale, Tailscale, one-use guest secret redemption, callback readiness, Android execution, physical gates, and product qcow2 semantics are not H02A work.
