# Hardware-independent development goal

## Objective

Reduce the eventual physical-device debugging surface and make each future development task independently runnable, reviewable, and evidence-bearing without claiming Android hardware success.

## Active cycle

The active task graph is `agents/task-dag.json`:

```text
H01  authenticated resumable artifact upload
H02  Ubuntu/QEMU/NoCloud/Headscale guest E2E on a Linux host
H03  managed-emulator Activity/Service/Room/API lifecycle suite
H04  harden the merged one-phone HIL evidence path
```

All four tasks are intentionally path-disjoint and may run in parallel.

## Orchestrator sequence

1. Run `make dev-plan`, `make validate`, and `make integration-worktree`.
2. Create the current wave with `make wave WAVE=1`.
3. Generate each scoped pack with `make context TASK=Hxx`.
4. Require packet-local tests and `python3 tools/agents/verify-scope.py Hxx`.
5. Integrate with `make integrate TASK=Hxx`.
6. Run `make dev-full` on the integration branch when the host has the Android toolchain.

## Rules

- Prefer functional vertical tests over broad refactors.
- Keep public APIs typed and preserve the host/guest identity split.
- Never weaken artifact SSRF policy to make local testing convenient; H01 adds a bounded upload path instead.
- Host-QEMU or emulator evidence is useful but cannot close B02, B07–B13, B16, or B17.
- `tests/hil/` is already the sole physical runner; H04 may harden it but must not create a parallel implementation.
- Do not start profile-registry, qcow2, source-native-build, or fuzzing follow-ons until the active cycle has landed or produced a focused blocker.
- Do not begin USB/AOA work.

## Completion report

Report integrated commits, exact commands, generated laboratory/evidence artifacts, unresolved blockers, and the next four-task cycle proposed from the results.
