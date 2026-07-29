# T03 — Durable store and NodeSupervisorService

## Outcome

Implement Room current state/journal, one reconciliation actor, and Android service lifecycle using a fake runtime first.

## Prerequisites

T01

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- One actor owns runtime mutations.
- Intent/result persists around side effects.
- Task removal does not alter desired state.
- Fake runtime recovers deterministically from simulated process death.
- Older generations and conflicting idempotency reuse are rejected.

## Required checks

```sh
make validate
cd android/podroid && ./gradlew :node-store:testDebugUnitTest :node-shell:testDebugUnitTest :test-support:testDebugUnitTest
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
