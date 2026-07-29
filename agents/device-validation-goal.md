# Goal: close the physical MVP gates

Use this goal after the T00–T08 software implementation cycle. The acceptance ledger, not task completion prose, defines success.

## Read first

1. `GOAL.md`
2. `docs/STATUS.md`
3. `docs/roadmap/device-validation.md`
4. the nearest `AGENTS.md` under `tests/device`, `tests/e2e`, and the component being debugged
5. only the evidence records for the gate currently being attempted

## Operating rules

- Test the exact CI artifact and record its SHA-256 before installation.
- One task closes one coherent physical boundary: D01 through D05.
- Never mark a gate `PASS` from a fake, JVM, emulator, code inspection, or manual assertion without the required device evidence.
- Preserve redaction; do not paste live auth keys, controller capabilities, private keys, VM disks, or unfiltered logs into prompts or commits.
- Prefer a narrow correction supported by a reproduced failure over speculative refactoring.
- Keep USB/AOA work blocked until D07.

## Completion

The run is complete only when every B gate has a machine-readable evidence record bound to one source commit, one exact APK, and the relevant device facts. A partial run should leave honest `BLOCKED-HARDWARE` or `FAIL` states and a focused reproduction command.
