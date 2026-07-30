# Git development cycle

## Branch model

- `main` — reviewed baseline with green CI.
- The active integration branch is read from `agents/task-dag.json` when a phase needs one.
- `agent/<task-id>-<slug>` — one active task packet in one worktree.
- `agent/<phase>-realignment` — narrow planning/status correction at a phase boundary.

Completed integration and task branches are historical provenance. Queued or merged packets are not reusable work authorization.

## Start the active phase

```sh
make install-hooks
make dev-plan
make validate
make status
make context TASK=F01
```

Verify phase entry criteria before creating implementation worktrees. The current `foundation-1` phase has one task, so a multi-worktree wave is unnecessary. Use `make wave` only when a later reviewed phase contains genuinely independent, path-disjoint tasks.

## Task cycle

```sh
make worktree TASK=F01
cd .worktrees/F01-canonical-artifact-profile-resolution
make context TASK=F01
# Read .local/context/F01.md plus applicable AGENTS.md files.
# Perform the packet's phase-start review before implementation.
python3 tools/agents/verify-scope.py F01
AGENT_MODEL='<exact runtime-reported model>' \
AGENT_RUN_ID='<stable runner id>' \
AGENT_TASK_ID=F01 \
AGENT_MODE=goal \
  tools/provenance/commit-agent.sh 'profiles: make packaged JSON authoritative'
```

The task worktree must be clean before handoff. If discovery changes the real scope, update the task packet and phase plan before continuing rather than silently crossing allowed paths.

## Integration

For a single-task phase, a focused PR from the tested task branch directly to `main` is preferred. An integration branch is useful only when the reviewed phase has multiple tasks that must be tested together.

Before merge:

1. task acceptance criteria pass;
2. phase exit criteria pass or the packet records a focused blocker;
3. scope verifier passes;
4. repository validation passes;
5. full applicable CI passes on the exact head;
6. evidence class is explicit.

Merge without rewriting the tested commits when possible. After merge, update the registry and roadmap with the merge SHA, then perform the next phase-start review before activating queued work.

## Commit policy

- Small, revertible commits.
- Functional source and broad generated output separated when practical.
- No history rewriting after handoff.
- Every agent commit carries exact provenance trailers.
- Never commit secrets or model conversation transcripts.
- Use only concrete `TODO(MVP-HARDENING, <task-id>)` comments with expiry triggers.

## Evidence policy

- Gate status changes require reviewed evidence records, not ownership by a historical task.
- Host-QEMU and emulator results never close physical gates.
- Physical evidence must identify the exact source commit, APK digest, device facts, scenario, commands, and assertions.
- A final MVP claim requires the relevant HIL scenarios to be run against one exact candidate after foundational/runtime changes have landed.
