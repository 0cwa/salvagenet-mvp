# Hardware-independent development goal

## Objective

Reduce the eventual physical-device debugging surface and make each future development task independently runnable, reviewable, and evidence-bearing without claiming Android hardware success.

## Current cycle state

The cycle definition remains in `agents/task-dag.json`; completion state is recorded in `agents/task-registry.json` and `docs/roadmap/hardware-independent.md`.

```text
H01  IN PROGRESS  authenticated resumable artifact upload
H02  PLANNED      Ubuntu/QEMU/NoCloud/Headscale guest E2E on a Linux host
H03  PLANNED      managed-emulator Activity/Service/Room/API lifecycle suite
H04  MERGED       hardened one-phone HIL evidence path
```

H04 landed on `main` in merge commit `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`. H01 has a first implementation on `agent/H01-artifact-upload`; it remains open until the recovery, cleanup, HTTP-semantics, publication-arbitration, and CI items in `agents/tasks/H01/task.md` are complete.

H02 and H03 remain path-disjoint and may begin independently. The cycle is not complete until H01–H03 have either landed or produced a documented focused blocker.

## Orchestrator sequence

1. Run `make dev-plan` and `make validate` on current `main` or the task branch.
2. Generate the scoped pack with `make context TASK=Hxx`.
3. Read the packet status before implementation; do not repeat already completed work.
4. Require packet-local tests and `python3 tools/agents/verify-scope.py Hxx`.
5. Open a focused PR against `main` and require the repository's full applicable workflow.
6. Update the packet, experiment record, and cycle-status documentation in the same branch whenever implementation findings change the true remaining work.

## Rules

- Prefer functional vertical tests over broad refactors.
- Keep public APIs typed and preserve the host/guest identity split.
- Never weaken artifact SSRF policy to make local testing convenient; H01 adds a bounded authenticated upload path instead.
- The resumable upload path and public HTTPS importer may share the artifact store only through an explicit publication-arbitration rule.
- Host-QEMU or emulator evidence is useful but cannot close B02, B07–B13, B16, or B17.
- `tests/hil/` is the sole physical runner. H04 is complete; subsequent HIL changes must use a new scoped task rather than silently extending H04.
- Do not start profile-registry, qcow2, source-native-build, or fuzzing follow-ons until the active cycle has landed or produced a focused blocker.
- Do not begin USB/AOA work.

## Completion report

Report integrated commits, exact commands, generated laboratory/evidence artifacts, unresolved blockers, and the next four-task cycle proposed from the results. Distinguish implemented, tested, merged, and physically validated states.
