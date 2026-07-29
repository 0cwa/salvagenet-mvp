# Repository instructions

## Read order

1. Read `GOAL.md`.
2. Read the task packet assigned under `agents/tasks/<TASK>/task.md`.
3. Run `python3 tools/agents/context-pack.py <TASK>` and read only the generated pack plus applicable nested `AGENTS.md` files.
4. Do not recursively read `docs/`; use `docs/INDEX.md` when more context is necessary.

## Development rules

- This is a modular monolith. Keep each change inside the task's allowed paths unless the task explicitly grants integration ownership.
- The domain/application center must not import Android, QEMU, Tailscale, Ktor, Room, Headscale, or Podroid types.
- Prefer new code in `android/modules/` beside Podroid. Modify `android/podroid/` only for a narrow composition hook or when the assigned migration task explicitly requires it.
- Preserve Podroid's executable-in-`nativeLibraryDir` QEMU launch, dedicated spawn/reap thread, launcher lifetime behavior, Unix sockets, and diagnostic learnings until an acceptance test proves a replacement.
- Public configuration and APIs must use typed fields. Never expose raw QEMU arguments, raw kernel arguments, raw QMP, or arbitrary shell strings.
- One VM is the MVP limit.
- USB networking is `MVP+`; do not start it while any base-MVP task is incomplete.
- Keep code simple. Comment non-obvious constraints and add `TODO(MVP-HARDENING, Txx)` for specifically deferred refinements.

## Verification

- Run the smallest relevant test first, then the task packet's required checks.
- Before handing off, run `python3 tools/agents/verify-scope.py <TASK>`.
- Report tests that could not run, especially physical-device, VPN-permission, or root-authorized checks.

## Git and provenance

- Work on the assigned `agent/<TASK>-<slug>` branch/worktree.
- Do not amend or rewrite another agent's commits.
- Use `tools/provenance/commit-agent.sh`; set `AGENT_MODEL`, `AGENT_RUN_ID`, and `AGENT_TASK_ID`.
- Keep commits small enough to revert independently. Generated files and source changes belong in separate commits when practical.
- Leave the worktree clean.
