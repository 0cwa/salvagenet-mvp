# Overnight operations

## Before launch

```sh
make doctor
make validate
make goal-preflight
make install-hooks
make lab-up
make lab-status
```

Import and baseline Podroid before parallel changes whenever possible. Confirm the physical phone remains connected, authorized, charged, thermally safe, and reachable from the Headscale lab host.

## Orchestrator behavior

- Follow `agents/task-dag.json`.
- Dispatch tasks only when prerequisites are merged or the task is explicitly scaffold-only.
- Use separate worktrees.
- Stop a task after repeated identical failure; record a focused blocker rather than broad rewrites.
- Prefer a working vertical slice over perfect abstractions.
- Never schedule T09 USB while a base acceptance item is red.

## Checkpoints

Suggested integration checkpoints:

1. baseline import/build;
2. contracts/profiles and QEMU compiler;
3. durable supervisor/store;
4. mesh and Host API;
5. end-to-end guest deployment;
6. QA/hardening;
7. optional USB decision.

## Recovery

The orchestrator should preserve failed worktrees. Do not delete unmerged branches. Use `tools/agents/status.py` to summarize task branch heads and tests, then resume from the smallest blocked packet.
