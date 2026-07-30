# Agent context engineering

## Objective

Give each implementation agent enough contract and local code to succeed without loading the whole architecture conversation or repository, while preventing queued, superseded, completed, or merely visible roadmap items from becoming accidental work authorization.

## Context layers

1. Root `AGENTS.md`: universal invariants and phase-boundary rules.
2. `agents/task-dag.json`: sole active phase, entry criteria, and exit criteria.
3. Compact generated roadmap index: current milestone and active/ready/blocked summaries after WEB04.
4. Nearest nested `AGENTS.md`: module-local constraints.
5. Active task packet: status, outcome, phase-start review, allowed paths, dependencies, compatibility policy, acceptance, verification, and handoff.
6. Generated task context pack: exact files listed by `context.list` plus applicable `AGENTS.md` files.
7. Bounded per-issue context: selected issue summary, dependencies, task/acceptance links, and current PR state; comments excluded by default.
8. On-demand index: `docs/INDEX.md`; agents fetch one additional page only when blocked.

## Rules

- `agents/task-dag.json` contains only active tasks. Merged, superseded, paused, and queued packets remain in `agents/task-registry.json` for provenance and later re-evaluation.
- GitHub issue visibility, dependency clarity, or an `agent:*` label is not implementation authority without the active DAG and reviewed packet.
- An inactive packet is not loaded automatically and is not implementation authority.
- The orchestrator does not paste the full roadmap, issue bodies, comments, or large design documents into prompts.
- Task packets link canonical files rather than duplicating them.
- `context-pack.py` enforces deterministic ordering and a byte budget.
- WEB04's per-issue context tool must enforce a separate byte/file limit and exclude comments by default.
- An agent may request an additional file by documenting why in its handoff; it should not recursively crawl `docs/` or GitHub history.
- Generated logs, build output, binary blobs, raw API responses, and secrets are never context inputs.
- The orchestrator integrates summaries, decisions, evidence, and tests, not private reasoning traces.

## Goal-mode prompt

Use `agents/hardware-independent-goal.md` for the current non-device phase. Device work uses `agents/device-validation-goal.md`. Create one worktree per active packet and merge only after packet acceptance, phase-exit verification, scope verification, applicable CI, and review pass.

The current task context command is:

```sh
make context TASK=WEB04
```

After WEB04, normal startup also runs `make roadmap-status`; a selected issue uses `make roadmap-context ISSUE=<number>` rather than loading the complete graph.

## Adding tasks

`tools/agents/new-task.py` creates **queued** packets by default. Use `--activate` only after a phase-boundary review has approved the task and its prerequisites. Expand the generated packet with concrete phase-start, compatibility, and phase-end checks before implementation. Run `make validate` immediately after writing or activating a task.

## Context hygiene

Keep architecture pages short and stable. Put volatile implementation observations in task experiment records and issue planning notes, not in `AGENTS.md`. Fold durable conclusions into the issue body, packet, ADR, experiment, or evidence before expecting another agent to use them. Put code-specific rationale next to the code when future maintainers need it.
