# T09 — USB networking MVP+

## Outcome

Only after base PASS, implement AOA-to-QEMU stream networking and Linux TAP/NAT as optional eth1.

## Prerequisites

T08 + BASE_MVP_PASS

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Gate passes before executable changes.
- AOA control link authenticates/reconnects.
- Guest receives eth1.
- Linux TAP/NAT provides internet.
- Disconnect returns to SLIRP.

## Required checks

```sh
python3 tools/ci/check-mvp-plus-gate.py
make validate
tests/usb/run.sh
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
