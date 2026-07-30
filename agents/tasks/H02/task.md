# H02 — Canonical Ubuntu guest boot qualification

## Status

**PLANNED — sole active task in phase `guest-boot-1`.**

## Outcome

Turn the existing host-QEMU laboratory into one deterministic qualification path for the exact checked-in Ubuntu profile and locked UEFI/image artifacts: real QMP running state, NoCloud completion, key-only SSH through loopback SLIRP, clean restart behavior, bounded evidence, and inspection for retained bootstrap secrets.

## Prerequisites

- F01 merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910`.
- Final F01 head `31dcd75199928b7887132a1429392266388c0b60` passed Actions run `30549498423`.
- The lab must consume the same checked-in profile and locked artifact identities that Android packages.

## Phase-start review

1. Run `make dev-plan`, `make validate`, `make test-guest`, and the smallest current host-QEMU smoke from current `main`.
2. Compare the lab profile/artifact inputs with `profiles/ubuntu-2404-arm64-uefi/profile.json` and `profiles/locks/images.lock.json`; remove any duplicate lab-owned profile definition.
3. Confirm the task remains independent of Headscale, guest Tailscale, emulator behavior, Android lifecycle, and physical-device gates.
4. Record unavailable host virtualization or firmware prerequisites honestly rather than replacing real QMP/SSH assertions with fakes.
5. Re-evaluate the acceptance criteria if the current lab proves that a smaller boundary is sufficient.

## Compatibility policy

None. This repository is unreleased alpha. Reset or recreate disposable host-QEMU state rather than adding migration, fallback, dual-read, or legacy-profile behavior. Any newly discovered compatibility requirement requires a separate authorized task and must not be added silently to this packet.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff and phase-plan review.

## Acceptance criteria

- One command prepares, boots, verifies, records, and cleans up the host-QEMU Ubuntu qualification run.
- The run records the exact canonical profile digest plus locked Ubuntu and AAVMF artifact identities.
- QEMU reaches a real `running` QMP status and cloud-init/NoCloud completion is observed through guest state rather than a test-owned marker.
- Key-only SSH succeeds through loopback SLIRP; password authentication remains disabled.
- A clean stop/start and guest restart return to the same qualified state without duplicate QEMU processes.
- Guest disk, cloud-init state, logs, and temporary metadata are inspected for retained one-use credentials or callback capabilities.
- Results are bounded, machine-readable, commit-bound, and explicitly classified as host-QEMU evidence rather than Android or physical-device evidence.
- No Headscale, guest-tailnet, emulator, USB, compatibility-migration, or unrelated product scope is introduced.

## Required checks

```sh
make validate
make test-guest
make qemu-lab-e2e
python3 tools/agents/verify-scope.py H02
```

The full applicable CI workflow must also pass before merge-ready status.

## Phase-end verification

1. Check every acceptance criterion against the exact code, lab output, and machine-readable evidence.
2. Confirm the lab uses canonical profile/lock inputs rather than a duplicate profile mirror.
3. Confirm evidence contains no live credentials and makes no Android/physical acceptance claim.
4. Record unavailable environmental checks and the smallest unresolved guest-boot ambiguity.
5. Re-evaluate guest-mesh qualification from the result; do not activate it automatically merely because H02 is complete.

## Handoff

Report commit SHA(s), exact checks, artifact identities, evidence paths, unavailable host prerequisites, every acceptance result, and the smallest next blocker. Keep guest Headscale/tailnet and emulator work queued for separate phase-start review.
