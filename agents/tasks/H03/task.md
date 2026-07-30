# H03 — Managed-emulator lifecycle suite

## Outcome

Add deterministic emulator/instrumentation coverage for Activity, foreground Service, Room, imported enrollment, fake runtime/mesh, API, package-replacement, and post-unlock reconciliation behavior.

## Prerequisites

None; active-cycle base is current `main`.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- CI can create and tear down the selected API 36 emulator without shared mutable AVD state.
- Activity recreation and task removal do not change desired runtime state.
- Service/application recreation reopens Room and resumes a fake in-flight operation exactly once.
- Enrollment import, VPN-permission-required UI, API authorization, idempotency, and old-generation rejection are exercised.
- Debug-only fault injectors are absent from release artifacts.
- Emulator results are labeled as emulator evidence and cannot close physical gates.

## Required checks

```sh
make validate
make emulator-install
make emulator-start
make test-emulator
make emulator-stop
```

## Handoff

Report commit SHA(s), exact tests and lab runs, evidence paths, checks unavailable in the current environment, concrete deferred items, and the smallest next blocker.
