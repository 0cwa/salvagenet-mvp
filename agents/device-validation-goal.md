# Goal: close physical MVP gates through the small HIL runner

Use this goal after the T00–T08 software cycle. The acceptance ledger, not task-completion prose, defines success.

## Read first

1. `GOAL.md`
2. `docs/STATUS.md`
3. `tests/hil/README.md`
4. `docs/roadmap/device-validation.md`
5. `tests/hil/AGENTS.md` and the nearest component `AGENTS.md`
6. only the gate evidence currently being attempted

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

A complete run has a local HIL evidence directory bound to one source commit, exact APK digest, configured device facts, recorded commands, and assertions. Promote reviewed evidence through the existing evidence tooling; never edit a gate to `PASS` based only on console prose.
