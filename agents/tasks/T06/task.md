# T06 — Typed Host API and MVP CLI

## Outcome

Implement OpenAPI resources behind replaceable server/auth ports plus a thin Python controller and recovery ProxyCommand.

## Prerequisites

T01

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Only bounded host resources are exposed.
- Mutations delegate idempotency/generation checks to node-core.
- No shell/QMP/argv fields.
- MVP auth is isolated behind `ControllerAuthenticator`.
- CLI drives the API and can operate as SSH ProxyCommand.

## Required checks

```sh
make validate
python3 -m unittest discover -s controller/mvp-cli/tests
cd android/podroid && ./gradlew :control-api:testDebugUnitTest
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
