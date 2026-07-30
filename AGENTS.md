# Repository instructions

## Read order

1. Read `GOAL.md`.
2. For ordinary implementation, read the active task packet named by `agents/task-dag.json` under `agents/tasks/<TASK>/task.md`.
3. For hardware-independent orchestration, read `agents/hardware-independent-goal.md`.
4. For physical validation, read `agents/device-validation-goal.md` and `tests/hil/AGENTS.md`; do not invent another physical runner.
5. Run `python3 tools/agents/context-pack.py <TASK>` for registered tasks and read only that pack plus applicable nested `AGENTS.md` files.
6. Do not recursively read `docs/`; use `docs/INDEX.md` when more context is necessary.

## Development rules

- This is a modular monolith. Keep each change inside the task's allowed paths unless the task explicitly grants integration ownership.
- The domain/application center must not import Android, QEMU, Tailscale, Ktor, Room, Headscale, or Podroid types.
- Prefer new code in `android/modules/` beside Podroid. Modify `android/podroid/` only for a narrow composition hook or when the assigned migration task explicitly requires it.
- Preserve Podroid's executable-in-`nativeLibraryDir` QEMU launch, dedicated spawn/reap thread, launcher lifetime behavior, Unix sockets, and diagnostic learnings until a physical acceptance test proves a replacement.
- Public configuration and APIs must use typed fields. Never expose raw QEMU arguments, raw kernel arguments, raw QMP, or arbitrary shell strings.
- One VM is the MVP limit.
- USB networking is `MVP+`; do not start it while any base-MVP gate is incomplete.
- Keep code simple. Comment non-obvious constraints and add `TODO(MVP-HARDENING, <task-id>)` only for specific deferred refinements with an expiry trigger.

## Hardware-in-the-loop rules

- `tests/hil/` is the sole physical-device scenario implementation. Existing `tests/device/` and `tests/e2e/` scripts are compatibility wrappers.
- Use only the exact ADB serial in `.local/hil.json`; never auto-select the first connected phone.
- Changes under `runtime-qemu` should run `hil-smoke` when an authorized configured phone is available.
- Changes under `mesh-tailscale`, `control-api`, profiles, or guest bootstrap should run `hil-mvp`.
- Changes to supervisor lifecycle, persistence, or reconciliation should run `hil-resilience`.
- A physical check may be reported `BLOCKED-HARDWARE` only after `hil-doctor` or the relevant scenario exits 77 and records the missing prerequisite.
- A fake, emulator, host-QEMU, code-review, or manual assertion does not close a physical gate.
- Do not add test-owned product state or a debug endpoint when the observation is available through the real Host API, ADB, Headscale, diagnostics, QMP-backed state, or SSH.

## Verification

- Run the smallest relevant test first, then the task packet or HIL scenario's required checks.
- Before handing off a registered task, run `python3 tools/agents/verify-scope.py <TASK>`.
- Report tests that could not run, especially physical-device, VPN-permission, reboot, or root-authorized checks.
- Physical evidence must identify the source commit, APK digest, configured device facts, scenario, commands, and assertions.

## Git and provenance

- Work on the assigned `agent/<TASK>-<slug>` branch/worktree, or a narrowly named validation branch when no registered task packet applies.
- Do not amend or rewrite another agent's commits.
- Use `tools/provenance/commit-agent.sh`; set `AGENT_MODEL`, `AGENT_RUN_ID`, and `AGENT_TASK_ID`.
- Keep commits small enough to revert independently. Generated files and source changes belong in separate commits when practical.
- Leave the worktree clean.
