# Overnight goal-mode handoff (historical cycle)

> T00–T08 have been implemented and integrated. Do not restart this task graph for current development. Use [`device-validation-goal.md`](device-validation-goal.md) and [`../docs/roadmap/device-validation.md`](../docs/roadmap/device-validation.md) to close the remaining physical MVP gates.

## Historical goal

Implement as much of the base NodeHost MVP as can be completed and verified in one overnight agent-day, preserving the working Podroid QEMU path and the scaffold's module boundaries.

## Start

1. Run `make goal-preflight`.
2. Read `GOAL.md`, root `AGENTS.md`, and `agents/task-dag.json`.
3. Confirm T00 import/baseline state.
4. Create separate worktrees and dispatch only eligible packets.
5. Merge in DAG order after packet-local tests and scope verification.

## Priorities

1. Keep imported Podroid buildable.
2. Reach a vertical path before polish: enrollment -> host mesh/API -> profile -> QEMU -> guest bootstrap -> SSH.
3. Use fakes for contract work when device/VPN authorization blocks hardware work.
4. Prefer wrappers and sibling modules over broad Podroid rewrites.
5. Mark only concrete deferrals `TODO(MVP-HARDENING, Txx)`.
6. Never expose raw QEMU/kernel args, QMP, or arbitrary shell through production interfaces.
7. Never start T09 while a base gate is red.

## Stop conditions

Report a focused blocker instead of repeated rewrites when the baseline is broken outside scope, authorization is missing, a prerequisite contract is unmerged, an identical failure persists after two evidence-driven attempts, or a proposed workaround violates a base invariant.

## Final report

List merged commits/trailers, tests run, physical tests passed or blocked, acceptance-ledger status, and the smallest next action for every blocker. Do not claim completion without evidence.
