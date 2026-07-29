# T05 — Embedded Android host mesh

## Outcome

Adapt official Android-aware libtailscale into `HostMesh` with Headscale URL, one-use auth key, encrypted state, and restart observations.

## Prerequisites

T00, T01, T04

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Adapter uses Android VpnService/platform hooks.
- Host key is deleted after enrollment.
- Imported URL/hostname/key reach the adapter.
- Port exposes typed status/addresses only.
- Restart/revoke/failure tests exist; missing VPN approval is reported honestly.

## Required checks

```sh
make validate
cd android/podroid && ./gradlew :mesh-tailscale:testDebugUnitTest :app:assembleDebug
tests/network/host-mesh/smoke.sh
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
