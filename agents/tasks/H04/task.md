# H04 — Physical evidence automation

## Outcome

Prepare a non-secret, exact-APK gate runner that captures device facts, package identity, process/QMP/mesh/API observations, redacts logs, and emits schema-valid evidence records for later borrowed or streamed devices.

## Prerequisites

None; active-cycle base is current `main`.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- `tests/device/run-gate.sh Bxx` validates prerequisites and binds output to source commit and APK SHA-256.
- Collectors are composable by gate and distinguish automatic assertions from manual observations.
- Logcat, process, QMP, Tailscale, listener, operation, and guest identity output is bounded and redacted.
- Interrupted runs retain a diagnostic bundle but never mark the gate PASS.
- Evidence JSON validates before replacing a gate record.
- The harness supports local ADB and documents a remote-device-streaming adapter seam.

## Required checks

```sh
make validate
python3 -m unittest discover -s tests/tools
tests/device/run-gate.sh --self-test
```

## Handoff

Report commit SHA(s), exact tests and lab runs, evidence paths, checks unavailable in the current environment, concrete TODOs, and the smallest next blocker.
