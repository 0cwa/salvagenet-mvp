# Agent context engineering

## Objective

Give each implementation agent enough contract and local code to succeed without loading the whole architecture conversation or repository.

## Context layers

1. Root `AGENTS.md`: universal invariants only.
2. Nearest nested `AGENTS.md`: module-local constraints.
3. Active task packet: outcome, allowed paths, dependencies, acceptance, and handoff.
4. Generated context pack: exact files listed by `context.list` plus applicable `AGENTS.md` files.
5. On-demand index: `docs/INDEX.md`; agents fetch one additional page only when blocked.

## Rules

- `agents/task-dag.json` describes the active cycle; completed packets stay in Git as provenance but are not loaded automatically.
- The orchestrator does not paste large design documents into prompts.
- Task packets link canonical files rather than duplicate them.
- `context-pack.py` enforces deterministic ordering and a byte budget.
- An agent may request an additional file by documenting why in its handoff; it should not recursively crawl `docs/`.
- Generated logs, build output, and binary blobs are never context inputs.
- The orchestrator integrates summaries and tests, not private reasoning traces.

## Goal-mode prompt

Use the goal named for the active cycle—currently `agents/hardware-independent-goal.md`. Device work uses `agents/device-validation-goal.md`; the completed overnight goal is historical. Create one worktree per active packet and merge only after packet-local tests and scope verification pass.

## Adding tasks

Use `tools/agents/new-task.py` so packet files, manifests, context limits, IDs, dependencies, and repository-relative paths are checked together. Run `make validate` immediately after writing a new task.

## Context hygiene

Keep architecture pages short and stable. Put volatile observations in `docs/research/experiment-register.md`, not in `AGENTS.md`. Put code-specific rationale next to the code when future maintainers need it.
