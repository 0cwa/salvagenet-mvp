# Goal: close physical MVP gates through the small HIL runner

The acceptance ledger, not task-completion prose, defines physical success. Physical diagnostics may run whenever an authorized device is available, but final gate promotion must be bound to the exact candidate commit, packaged profiles, and APK after relevant foundational/runtime changes land.

## Read first

1. `GOAL.md`
2. `docs/STATUS.md`
3. `agents/task-dag.json` and the active packet, to understand whether the APK is a diagnostic or final candidate
4. `tests/hil/README.md`
5. `docs/roadmap/device-validation.md`
6. `tests/hil/AGENTS.md` and the nearest component `AGENTS.md`
7. only the gate evidence currently being attempted

## Phase relationship

- During F01, an HIL smoke or focused scenario is useful diagnostic evidence but cannot be the final MVP seal because production profile/artifact resolution is changing.
- At each later phase start, decide which physical scenario will most cheaply validate the assumptions being changed.
- At each phase end, record physical checks that ran or were unavailable; do not delay all device contact until the end when an early run can expose a foundational mismatch.
- Re-run all gate-relevant scenarios on one exact final candidate before promoting the complete MVP evidence set.

## Operating rules

- Use one explicitly configured ADB serial; never auto-select a device.
- Test the exact APK and record its SHA-256 before installation.
- Run `hil-smoke`, `hil-mvp`, or `hil-resilience`; do not create a parallel physical-test script.
- Only a physical HIL run may close a physical gate.
- `BLOCKED-HARDWARE` requires `hil-doctor` or scenario evidence ending in exit 77.
- Keep enrollment keys, controller capabilities, private keys, guest disks, and unfiltered logs out of prompts and commits.
- Prefer the smallest correction reproduced by the HIL run over speculative refactoring.
- Keep USB/AOA blocked until every base gate passes.

## Completion

A promotable run has a local HIL evidence directory bound to one source commit, exact APK digest, packaged profile/artifact facts where relevant, configured device facts, recorded commands, and assertions. Promote reviewed evidence through the existing tooling; never edit a gate to PASS based only on console prose.
