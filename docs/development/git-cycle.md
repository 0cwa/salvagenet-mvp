# Git development cycle

## Branch model

- `main` — reviewed baseline with green CI.
- The active integration branch is read from `agents/task-dag.json`.
- `agent/<task-id>-<slug>` — one active task packet in one worktree.

Completed integration and task branches are historical provenance; new work follows the active graph rather than reusing an old cycle name.

## Initialize the active cycle

```sh
make install-hooks
make integration-worktree
make wave WAVE=1
make status
```

`make integration-worktree` fails if `.worktrees/integration` is still attached to a different cycle. `make wave` refuses to create a later wave until its prerequisites are merged into the active integration branch. USB tasks also require the base-MVP acceptance gate.

## Task cycle

```sh
make worktree TASK=H01
cd .worktrees/H01-artifact-upload
make context TASK=H01
# Read .local/context/H01.md plus applicable AGENTS.md files.
# Implement and run the packet's smallest checks.
python3 tools/agents/verify-scope.py H01
AGENT_MODEL='<exact runtime-reported model>' \
AGENT_RUN_ID='<stable runner id>' \
AGENT_TASK_ID=H01 \
AGENT_MODE=goal \
  tools/provenance/commit-agent.sh 'control-api: add resumable artifact upload'
```

The task worktree must be clean before integration.

## Orchestrator integration

```sh
make integrate TASK=H01
make status
```

The integration helper verifies scope, cleanliness, prerequisite order, merges without rewriting the agent commit, and runs repository validation. It stops on conflicts rather than inventing a resolution. Resolve conflicts in the integration worktree with the relevant task packet and both module-level `AGENTS.md` files in context.

After all active tasks are integrated:

```sh
make -C .worktrees/integration dev-full
# Open a pull request from the integration branch to main.
```

Require green CI and review before merging to `main`; do not carry an old integration branch forward into the next cycle.

## Commit policy

- Small, revertible commits.
- Functional source and broad generated output separated when practical.
- No history rewriting after handoff.
- Every agent commit carries exact provenance trailers.
- Never commit secrets or model conversation transcripts.
- Use only concrete `TODO(MVP-HARDENING, <task-id>)` comments with expiry triggers.

## Merge and evidence policy

1. Task-local acceptance green.
2. Scope verifier green.
3. Prerequisites already integrated.
4. Repository validation green after merge.
5. CI green on the integration pull request.
6. Evidence class stated explicitly; host-QEMU/emulator results never close physical gates.
7. The task designated by the active cycle owns shared status/evidence promotion.
