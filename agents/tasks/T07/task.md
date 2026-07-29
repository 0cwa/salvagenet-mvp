# T07 — Vertical Android integration

## Outcome

Compose adapters and prove enrollment -> host mesh/API -> profile/QEMU -> guest bootstrap/mesh/SSH with recovery.

## Prerequisites

T02, T03, T04, T05, T06

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Enrollment drives host mesh and controller auth.
- Controller applies an Ubuntu VM generation.
- Guest joins separately and is key-only SSH reachable.
- Recovery SSH works without guest mesh.
- Controller disconnect leaves desired state unchanged.
- Unrun hardware tests are marked blocked.

## Required checks

```sh
make validate
cd android/podroid && ./gradlew :app:assembleDebug
tests/e2e/run.sh
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
