# Git development cycle

## Branch model

- `main` — clean handoff baseline; fast-forward only after integration is green.
- `integration/mvp-night` — orchestrator-owned ordered merge branch.
- `agent/Txx-slug` — one task packet in one worktree.

No implementation agent writes directly to `main` or the integration branch.

## Initialize the night

```sh
make install-hooks
make integration-worktree
make wave WAVE=1
make status
```

`make wave` refuses to create a later wave until all of its task prerequisites
are merged into the integration branch. The USB wave also checks the base-MVP
acceptance ledger.

## Task cycle

```sh
make worktree TASK=T02
cd .worktrees/T02-qemu-adapter
make context TASK=T02
# Read .local/context/T02.md plus applicable AGENTS.md files.
# Implement and run the task packet's smallest checks.
python3 tools/agents/verify-scope.py T02
AGENT_MODEL='<exact runtime-reported model>' \
AGENT_RUN_ID='<stable runner id>' \
AGENT_TASK_ID=T02 \
AGENT_MODE=goal \
  tools/provenance/commit-agent.sh 'runtime-qemu: preserve typed launch invariants'
```

The task worktree must be clean before integration.

## Orchestrator integration

```sh
make integrate TASK=T02
make status
```

The integration helper verifies task scope, cleanliness, prerequisite order,
merges without rewriting the agent commit, and runs the repository validation
suite. It stops on conflicts rather than inventing a resolution. The
orchestrator resolves a conflict in the integration worktree with the relevant
task packet and both module AGENTS files in context.

After all base tasks are integrated and verified:

```sh
git switch main
git merge --ff-only integration/mvp-night
make validate
```

## Commit policy

- Small, revertible commits.
- Functional source and broad generated output separated when practical.
- No history rewriting after handoff.
- Every agent commit carries exact provenance trailers.
- Never commit secrets or model conversation transcripts.
- Use only concrete `TODO(MVP-HARDENING, Txx)` comments.

## Merge and evidence policy

1. Task-local acceptance green.
2. Scope verifier green.
3. Prerequisites already integrated.
4. Repository validation green after merge.
5. Physical checks recorded as `PASS` or `BLOCKED-HARDWARE`, never inferred.
6. T08 alone promotes task-local experiment notes into the shared ledger.
