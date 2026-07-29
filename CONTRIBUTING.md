# Contributing

This repository is optimized for parallel agent work without losing architectural control.

1. Read `GOAL.md` and the applicable `AGENTS.md` files.
2. Select one task packet under `agents/tasks/`.
3. Create the task worktree with `tools/agents/create-worktree.sh`.
4. Build a scoped context pack with `make context TASK=Txx`.
5. Change only the task's allowed paths.
6. Run the packet's acceptance commands and `tools/agents/verify-scope.py Txx`.
7. Commit through `tools/provenance/commit-agent.sh`.
8. Leave a clean worktree and a handoff note in the task branch commit body or PR.

The default development cycle is described in `docs/development/git-cycle.md`.
