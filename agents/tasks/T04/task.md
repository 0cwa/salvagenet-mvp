# T04 — Headscale lab and guest-init assets

## Outcome

Make the disposable Headscale lab operational and implement trusted NoCloud/bootstrap/K3s-qualification assets.

## Prerequisites

None

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Config renders with a phone-reachable URL.
- Container configtest and health pass when authorized.
- Separate one-use host/guest keys go to ignored files.
- Guest bootstrap installs key-only SSH/Tailscale through one-time redemption.
- K3s qualifier emits JSON and never joins a cluster.

## Required checks

```sh
make validate
make lab-up
make lab-keys
make lab-status
make lab-down
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
