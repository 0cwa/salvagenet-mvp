# H03 — Managed-emulator lifecycle suite

## Status

**QUEUED FOR PHASE-START REVIEW — not active work.**

H03 may be activated only after F01 is merged and the next phase review confirms which lifecycle ambiguities still need emulator coverage before scarce physical-device sessions.

## Provisional outcome

Add deterministic emulator/instrumentation coverage for Activity, foreground Service, Room, imported enrollment, fake runtime/mesh, API, package replacement, and post-unlock reconciliation behavior.

## Required phase-start review

Before activation:

1. Re-run the current JVM and Android unit suites and identify lifecycle behaviors that cannot be tested adequately without an emulator.
2. Decide whether H03 should split into:
   - a reproducible, stateless API 36 emulator harness; and
   - product lifecycle/instrumentation scenarios.
3. Remove scenarios already proved by unit/contract tests and avoid test-only product state or debug endpoints.
4. Confirm fake runtime/mesh adapters exercise real application ports and cannot enter release artifacts.
5. Revalidate that emulator evidence cannot update physical acceptance gates.

## Provisional acceptance criteria

- CI can create and tear down the selected API 36 emulator without shared mutable AVD state.
- Activity recreation and task removal do not change desired runtime state.
- Service/application recreation reopens Room and resumes a fake in-flight operation exactly once.
- Enrollment import, VPN-permission-required UI, API authorization, idempotency, and old-generation rejection are exercised only where emulator behavior adds value beyond unit tests.
- Debug-only fault injectors and fake adapters are absent from release artifacts.
- Emulator results are explicitly labeled and cannot close physical gates.

## Provisional checks

```sh
make validate
make emulator-install
make emulator-start
make test-emulator
make emulator-stop
python3 tools/agents/verify-scope.py H03
```

## Handoff

Do not begin from this packet as written. At the next phase boundary, revise its scope, dependencies, allowed paths, acceptance criteria, and evidence expectations before changing implementation files.
