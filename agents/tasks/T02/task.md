# T02 — Podroid-derived QEMU adapter

## Outcome

Wrap/extract Podroid QEMU behavior into `runtime-qemu`, add typed compilation/profile resolution, and preserve launch knowledge in tests.

## Prerequisites

T00, T01

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Launch remains nativeLibraryDir -> launcher -> QEMU on dedicated spawn/reap thread.
- Alpine compiler output preserves baseline invariants.
- Ubuntu UEFI output has no Alpine filenames.
- QMP is internal to the adapter.
- Management forwards bind loopback.
- Paths are instance-scoped.

## Required checks

```sh
make validate
cd android/podroid && ./gradlew :runtime-qemu:testDebugUnitTest :app:assembleDebug
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
