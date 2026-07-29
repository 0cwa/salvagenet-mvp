# T00 — Import and baseline Podroid

## Outcome

Import the pinned Podroid snapshot, wire sibling modules, and capture a reproducible known-good baseline.

## Prerequisites

None

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Podroid is present at the lock commit.
- Gradle settings include every sibling module exactly once.
- Baseline build runs or has a precise environment blocker.
- Current QEMU argv is captured before refactoring.
- No node-host business logic is scattered through Podroid UI.

## Required checks

```sh
make validate
python3 tools/bootstrap/wire-podroid.py --check
cd android/podroid && ./gradlew :app:testDebugUnitTest :app:assembleDebug
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
