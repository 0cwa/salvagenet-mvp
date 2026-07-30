# Git development cycle

## Branch model

- `main` — reviewed baseline with green CI.
- The active integration branch is read from `agents/task-dag.json` when a phase needs one.
- `agent/<task-id>-<slug>` — one active task packet in one worktree.
- `agent/<phase>-realignment` — narrow planning/status correction at a phase boundary.

Completed integration and task branches are historical provenance. Queued, paused, superseded, or merged packets and visible GitHub issues are not reusable work authorization.

## Start the active phase

```sh
make install-hooks
make dev-plan
make validate
make status
make context TASK=WEB04
```

Verify phase entry criteria before creating implementation worktrees. The current `roadmap-foundation-1` phase has one task, so a multi-worktree wave is unnecessary. Use `make wave` only when a later reviewed phase contains genuinely independent, path-disjoint tasks.

## Task cycle

```sh
make worktree TASK=WEB04
cd .worktrees/WEB04-issue-roadmap-and-human-aware-agent-index
make context TASK=WEB04
# Read .local/context/WEB04.md plus applicable AGENTS.md files.
# Reconfirm the packet's phase-start findings before implementation.
python3 tools/agents/verify-scope.py WEB04
AGENT_MODEL='<exact runtime-reported model>' \
AGENT_RUN_ID='<stable runner id>' \
AGENT_TASK_ID=WEB04 \
AGENT_MODE=goal \
  tools/provenance/commit-agent.sh 'roadmap: bootstrap live issue graph and agent index'
```

The task worktree must be clean before handoff. If discovery changes the real scope, update the active issue, task packet, and phase plan before continuing rather than silently crossing allowed paths.

## Integration

For a single-task phase, a focused PR from the tested task branch directly to `main` is preferred. An integration branch is useful only when the reviewed phase has multiple tasks that must be tested together.

Before merge-ready:

1. task acceptance criteria pass;
2. phase exit criteria pass or the packet records a focused blocker;
3. scope verifier passes;
4. repository validation passes;
5. full applicable CI passes on the exact head;
6. evidence or live-state class is explicit;
7. actionable review findings are resolved or dispositioned.

After approval, merge the exact tested head without rewriting it when possible. Then update the registry, roadmap issue, and experiment with the merge SHA, and perform the next phase-start review before activating queued work.

## Commit policy

- Small, revertible commits.
- Functional source and broad generated output separated when practical.
- No history rewriting after handoff.
- Every agent commit carries exact provenance trailers.
- Never commit secrets, raw GitHub responses, or model conversation transcripts.
- Use only concrete `TODO(MVP-HARDENING, <task-id>)` comments with expiry triggers.

## Evidence and state policy

- Gate status changes require reviewed evidence records, not issue or task completion.
- Host-QEMU, emulator, roadmap, website, and code-review results never close physical gates.
- Live roadmap apply must identify the exact source, seed/schema version, workflow, object counts, source hash, and rerun result.
- Physical evidence must identify the exact source commit, APK digest, device facts, scenario, commands, and assertions.
- A final MVP claim requires the relevant HIL scenarios to be run against one exact candidate after foundational/runtime changes have landed.
