# Repository instructions

## Read order

1. Read `GOAL.md`.
2. Read `agents/task-dag.json` for the sole active phase and `agents/task-registry.json` for status/provenance.
3. Read the active packet under `agents/tasks/<TASK>/task.md`; queued or merged packets are not work authorization.
4. For hardware-independent orchestration, read `agents/hardware-independent-goal.md`.
5. For physical validation, read `agents/device-validation-goal.md` and `tests/hil/AGENTS.md`; do not invent another physical runner.
6. Run `python3 tools/agents/context-pack.py <TASK>` and read only that pack plus applicable nested `AGENTS.md` files.
7. Do not recursively read `docs/`; use `docs/INDEX.md` when more context is necessary.

## Phase-boundary rules

- At phase start, verify current `main`, run `make dev-plan` and `make validate`, then re-evaluate task necessity, prerequisites, dependencies, allowed paths, acceptance criteria, and evidence limits.
- Keep only current-phase tasks in `agents/task-dag.json`. Retain merged and queued packets in the registry for provenance.
- During implementation, update the task packet and experiment record when discovery changes the real problem.
- At phase end, check every task acceptance criterion and phase exit criterion against code, tests, package artifacts, and evidence before activating the next phase.
- Merge the exact tested head, record the merge SHA, then revise, split, remove, reorder, or activate queued tasks from the result.

## Development rules

- This is a modular monolith. Keep each change inside the task's allowed paths unless the task explicitly grants integration ownership.
- The domain/application center must not import Android, QEMU, Tailscale, Ktor, Room, Headscale, or Podroid types.
- Prefer new code in `android/modules/` beside Podroid. Modify `android/podroid/` only for a narrow composition/packaging hook or an explicitly assigned migration.
- Preserve Podroid's executable-in-`nativeLibraryDir` QEMU launch, dedicated spawn/reap thread, launcher lifetime behavior, Unix sockets, and diagnostic learnings until physical acceptance proves a replacement.
- Public configuration and APIs must use typed fields. Never expose raw QEMU arguments, raw kernel arguments, raw QMP, arbitrary shell strings, or arbitrary host file paths.
- One VM is the MVP limit.
- USB networking is MVP+; do not start it while any base-MVP gate is incomplete.
- Kotlin/Compose/Hilt/Python/Ktor/Room are current MVP implementations, not permission to couple permanent contracts to them or preclude later Slint/Rust/shared-controller ADRs.
- Keep code simple. Add `TODO(MVP-HARDENING, <task-id>)` only for a specific deferred refinement with an expiry trigger.

## Hardware-in-the-loop rules

- `tests/hil/` is the sole physical-device scenario implementation. Existing `tests/device/` and `tests/e2e/` scripts are compatibility wrappers.
- Use only the exact ADB serial in `.local/hil.json`; never auto-select the first connected phone.
- Changes under `runtime-qemu` should run `hil-smoke` when an authorized configured phone is available.
- Changes under `mesh-tailscale`, `control-api`, profiles, artifact consumption, or guest bootstrap should run `hil-mvp` when the phase reaches physical validation.
- Changes to supervisor lifecycle, persistence, or reconciliation should run `hil-resilience`.
- A physical check may be reported `BLOCKED-HARDWARE` only after `hil-doctor` or the relevant scenario exits 77 and records the missing prerequisite.
- A fake, emulator, host-QEMU, package build, code review, or manual assertion does not close a physical gate.
- Do not add test-owned product state or a debug endpoint when observation is available through the real Host API, ADB, Headscale, diagnostics, QMP-backed state, or SSH.

## Verification

- Run the smallest relevant test first, then the task packet's required checks.
- Before handing off a registered task, run `python3 tools/agents/verify-scope.py <TASK>`.
- Report tests that could not run, especially physical-device, VPN-permission, reboot, storage-pressure, or root-authorized checks.
- Physical evidence must identify the source commit, APK digest, configured device facts, scenario, commands, and assertions.

## Git and provenance

- Work on the assigned `agent/<TASK>-<slug>` branch/worktree, or a narrowly named phase-realignment branch when no implementation packet applies.
- Do not amend or rewrite another agent's commits.
- Use `tools/provenance/commit-agent.sh`; set `AGENT_MODEL`, `AGENT_RUN_ID`, and `AGENT_TASK_ID`.
- Keep commits small enough to revert independently. Generated files and source changes belong in separate commits when practical.
- Leave the worktree clean.
