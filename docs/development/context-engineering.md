# Agent context engineering

## Objective

Give each implementation agent enough durable direction, current milestone context, contract, and local code to succeed without loading the whole architecture conversation or repository, while preventing queued, superseded, completed, or merely visible roadmap items from becoming accidental work authorization.

## Context layers

1. `docs/product/north-star.md`: durable SalvageNet mission, platform order, and product boundary.
2. `GOAL.md`: bounded current milestone and explicit non-goals.
3. Root `AGENTS.md`: universal invariants and phase-boundary rules.
4. `agents/task-dag.json`: sole active phase, entry criteria, and exit criteria.
5. Compact generated roadmap index: current milestone and active/ready/blocked summaries.
6. Nearest nested `AGENTS.md`: module-local constraints.
7. Active task packet: status, outcome, phase-start review, allowed paths, dependencies, compatibility policy, acceptance, verification, and handoff.
8. Generated task context pack: the three core files above, exact files listed by `context.list`, and applicable nested `AGENTS.md` files.
9. Bounded per-issue context: selected issue summary, dependencies, task/acceptance links, and current PR state; comments excluded by default.
10. On-demand index: `docs/INDEX.md`; agents fetch one additional page only when blocked.

The full strategic roadmap is not injected into every implementation pack. Phase planning reads `docs/roadmap/strategic-priorities.md` and the bounded selected issue context separately.

## Rules

- `agents/task-dag.json` contains only active tasks. Merged, superseded, paused, and queued packets remain in `agents/task-registry.json` for provenance and later re-evaluation.
- GitHub issue visibility, dependency clarity, or an `agent:*` label is not implementation authority without the active DAG and reviewed packet.
- `roadmap-authorization.yml` projects the DAG into `agent:active`; the live snapshot independently fails on disagreement.
- An inactive packet is not loaded automatically and is not implementation authority.
- The orchestrator does not paste the full roadmap, issue bodies, comments, or large design documents into prompts.
- Task packets link canonical files rather than duplicating them.
- `context-pack.py` prepends the north star, current milestone, and root repository rules, then enforces deterministic ordering and a byte budget.
- The per-issue context tool enforces a separate byte/file limit and excludes comments by default.
- An agent may request an additional file by documenting why in its handoff; it should not recursively crawl `docs/` or GitHub history.
- Generated logs, build output, binary blobs, raw API responses, and secrets are never context inputs.
- The orchestrator integrates summaries, decisions, evidence, and tests, not private reasoning traces.

## Goal-mode prompt

Use `agents/hardware-independent-goal.md` for a current non-device phase. Device work uses `agents/device-validation-goal.md`. Create one worktree per active packet and merge only after packet acceptance, phase-exit verification, scope verification, applicable CI, and review pass.

The current task context command is:

```sh
make context TASK=H02A
```

Normal startup also runs `make roadmap-status`; a selected issue uses `make roadmap-context ISSUE=<stable-id>` rather than loading the complete graph.

## Adding tasks

`tools/agents/new-task.py` creates **queued** packets by default. Use `--activate` only after a phase-boundary review has approved the task and its prerequisites. Expand the generated packet with concrete phase-start, compatibility, and phase-end checks before implementation.

A phase transition must:

1. update the GitHub issue planning state and dependencies as needed;
2. place only the approved task or path-disjoint set in `agents/task-dag.json`;
3. ensure each active task packet is linked by the issue's hidden task-packet marker;
4. let the authorization workflow synchronize `agent:active` and fail if it cannot;
5. run `make validate` before implementation.

## Context hygiene

Keep architecture pages short and stable. Put volatile implementation observations in task experiment records and issue planning notes, not in `AGENTS.md`. Fold durable conclusions into the issue body, packet, ADR, experiment, or evidence before expecting another agent to use them. Put code-specific rationale next to the code when future maintainers need it.
