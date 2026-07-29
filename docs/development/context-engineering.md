# Agent context engineering

## Objective

Give each implementation agent enough contract and local code to succeed without loading the whole architecture conversation or repository.

## Context layers

1. Root `AGENTS.md`: universal invariants only.
2. Nearest nested `AGENTS.md`: module-local constraints.
3. Task packet: outcome, allowed paths, dependencies, acceptance, and handoff.
4. Generated context pack: exact files listed by `context.list` plus applicable AGENTS files.
5. On-demand index: `docs/INDEX.md`; agents fetch one additional page only when blocked.

## Rules

- The orchestrator does not paste large design documents into prompts.
- Task packets link canonical files rather than duplicate them.
- `context-pack.py` enforces deterministic ordering and a byte budget.
- An agent may request an additional file by documenting why in its handoff; it should not recursively crawl `docs/`.
- Generated logs, build output, and binary blobs are never context inputs.
- The orchestrator integrates summaries and tests, not private reasoning traces.

## Goal-mode prompt

Use `agents/overnight-goal.md` as the root goal. The orchestrator should instantiate task packets according to `agents/task-dag.json`, create one worktree per task, and merge only after packet-local tests pass.

## Context hygiene

Keep architecture pages short and stable. Put volatile observations in `docs/research/experiment-register.md`, not in `AGENTS.md`. Put code-specific rationale next to the code when future maintainers need it.
