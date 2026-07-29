# T01 — Domain contracts, schemas, and profiles

## Outcome

Implement domain/use-case contracts plus validated enrollment/profile schemas and all three MVP profiles.

## Prerequisites

None

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Domain/application source imports no platform adapter types.
- All examples validate.
- Alpine, Ubuntu, and K3s-lab profiles resolve to one model.
- Generation and operation transitions have tests.
- Schemas accept no raw shell/QEMU/kernel argv.

## Required checks

```sh
make validate
cd android/podroid && ./gradlew :node-model:testDebugUnitTest :node-core:testDebugUnitTest
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
