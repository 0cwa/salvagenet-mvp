# Agent context engineering

## Objective

Give each implementation agent enough contract and local code to succeed without loading the whole architecture conversation or repository, while preventing queued or completed plans from becoming accidental work authorization.

## Context layers

1. Root `AGENTS.md`: universal invariants and phase-boundary rules.
2. `agents/task-dag.json`: sole active phase, entry criteria, and exit criteria.
3. Nearest nested `AGENTS.md`: module-local constraints.
4. Active task packet: status, outcome, phase-start review, allowed paths, dependencies, acceptance, verification, and handoff.
5. Generated context pack: exact files listed by `context.list` plus applicable `AGENTS.md` files.
6. On-demand index: `docs/INDEX.md`; agents fetch one additional page only when blocked.

## Rules

- `agents/task-dag.json` contains only active tasks. Merged and queued packets remain in `agents/task-registry.json` for provenance and later re-evaluation.
- A queued packet is not loaded automatically and is not implementation authority.
- The orchestrator does not paste large design documents into prompts.
- Task packets link canonical files rather than duplicating them.
- `context-pack.py` enforces deterministic ordering and a byte budget.
- An agent may request an additional file by documenting why in its handoff; it should not recursively crawl `docs/`.
- Generated logs, build output, and binary blobs are never context inputs.
- The orchestrator integrates summaries and tests, not private reasoning traces.

## Goal-mode prompt

Use `agents/hardware-independent-goal.md` for the current foundation phase. Device work uses `agents/device-validation-goal.md`. Create one worktree per active packet and merge only after packet acceptance, phase-exit verification, scope verification, and applicable CI pass.

## Adding tasks

`tools/agents/new-task.py` creates **queued** packets by default. Use `--activate` only after a phase-boundary review has approved the task and its prerequisites. Expand the generated packet with concrete phase-start and phase-end checks before implementation. Run `make validate` immediately after writing or activating a task.

## Context hygiene

Keep architecture pages short and stable. Put volatile implementation observations in task experiment records, not in `AGENTS.md`. Put code-specific rationale next to the code when future maintainers need it.
