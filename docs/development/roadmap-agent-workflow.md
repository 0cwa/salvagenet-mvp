# Roadmap and agent workflow

## Objective

Let GitHub Issues describe the complete project path while keeping agent context small and preserving the repository's phase-boundary discipline.

The roadmap is a planning graph, not a standing instruction to implement every visible issue.

## Agent start sequence

Before roadmap or implementation work, an agent must:

1. read `GOAL.md` and the root `AGENTS.md`;
2. inspect the compact generated roadmap index;
3. check whether the local roadmap snapshot is current;
4. read only the assigned issue and active task packet;
5. confirm that the issue is dependency-clear and the packet is authorised in `agents/task-dag.json`;
6. stop and request a phase review when those sources disagree.

The roadmap tooling phase will provide these commands:

```sh
make roadmap-status
make roadmap-check
make roadmap-sync
make roadmap-context ISSUE=123
make context TASK=H02A
```

Until those commands exist, `agents/task-dag.json`, the active packet, and `docs/roadmap/public-roadmap-governance.md` are the relevant sources.

## Compact generated state

The generator writes a small ignored local cache and a small committed/public snapshot.

### Public website snapshot

```text
website/data/roadmap.snapshot.v1.json
```

Contains:

- schema version;
- generation time;
- source repository and source hash;
- fallback/staleness metadata;
- milestones;
- issue number, title, public summary, URL, milestone, labels, dependency IDs, and derived states.

It does not contain full issue bodies, comments, review threads, logs, attachments, or secrets.

### Agent index

```text
agents/generated/roadmap.index.v1.json
```

Contains only:

- current milestone;
- active, ready, and blocked issue summaries;
- stable roadmap IDs and issue numbers;
- dependency numbers;
- task-packet paths;
- acceptance IDs;
- source hash and generation time.

The index is intended to fit in normal orchestrator context without loading the complete roadmap.

### Local cache

```text
.agent-cache/roadmap/
├── roadmap.v1.json
├── etags.json
└── fetched-at.json
```

This directory is ignored by Git. It may contain fetch metadata and the current normalized graph, but not credentials or raw issue comments.

## Per-issue context

`make roadmap-context ISSUE=<number>` produces a bounded context pack containing:

- issue title and public summary;
- observable outcome;
- milestone and labels;
- blockers and items unblocked;
- acceptance IDs;
- task-packet path;
- declared context paths;
- linked pull requests and current review state;
- latest concise planning note when present.

Comments are history, not canonical context. They are excluded by default.

An explicit debug option may include a small, newest-first, byte-limited comment selection. Important conclusions must be folded into the issue body, task packet, ADR, experiment record, or acceptance evidence.

## Freshness policy

The roadmap fetcher records:

- `generatedAt`;
- newest issue update time;
- source hash;
- whether live data or fallback was used;
- snapshot age.

Policy:

```text
Live fetch succeeds
    publish the validated live snapshot

Live fetch fails and snapshot age <= 72 hours
    use the last complete snapshot and display last-sync information

Live fetch fails and snapshot age > 72 hours
    fail the new site deployment and keep the previous deployment online

Structural roadmap validation fails
    fail immediately; do not hide the error with a snapshot
```

A partial dependency fetch is treated as a failed live fetch. It must never publish a graph that incorrectly shows blocked work as ready.

## Work-state and dependency-state separation

The generator derives two separate concepts.

### Work state

```text
planned
ready
active
review
hold
done
```

### Dependency state

```text
clear
blocked
```

A closed issue is `done`. An open issue with an unresolved dependency is `blocked` regardless of its agent label. An issue without blockers is not automatically ready; `agent:ready` still requires a phase-start review and a reviewed packet.

## Phase-start review

Before activating the next issue:

1. refresh the roadmap and acceptance status;
2. verify current `main` and the exact previous merge result;
3. identify the smallest unresolved uncertainty on the critical path;
4. re-evaluate every queued issue whose premise may have changed;
5. split, merge, reorder, defer, or remove issues as evidence requires;
6. confirm acceptance coverage and durable-goal alignment;
7. create or revise the task packet;
8. verify allowed paths and context limits;
9. update issue dependencies and agent-state labels;
10. place only the authorised current phase in `agents/task-dag.json`.

The phase-transition PR records the planning rationale. It should explain why the selected issue is now the smallest useful next step and why nearby queued work remains queued, changed, or removed.

## During implementation

Discovery may change the real problem.

The implementation branch may update:

- the active issue's outcome, acceptance criteria, context paths, or non-goals;
- the active task packet;
- the experiment record;
- directly affected dependency links.

Large roadmap reshaping belongs in a phase-transition or governance PR, not hidden inside an unrelated implementation commit.

## Phase end

### Before merge-ready status

1. verify every issue and task acceptance criterion;
2. run all required checks and inspect relevant artifacts;
3. record unavailable physical checks honestly;
4. record the exact tested head and evidence identity;
5. update the issue and task record to `review` or `merge-ready` without closing them;
6. resolve or explicitly disposition every actionable review finding;
7. confirm the exact final head still passes the required checks.

### After approval and merge

1. merge the exact tested and reviewed head;
2. record the merge SHA and evidence result in the issue, packet, registry, and experiment record as applicable;
3. close the issue only when its implementation outcome is complete;
4. leave acceptance gates unchanged unless their own required evidence passed;
5. run the next phase-start review instead of automatically activating the next queued issue.

This preserves distinct `active`, `review` or `merge-ready`, and `merged` states. An implementation is never merged merely because its first test run passed.

## Alignment guardrails

Agents may reshape the roadmap freely at phase boundaries when the following remain true:

- `GOAL.md` and accepted ADRs are not silently weakened;
- B01–B20 and U01–U04 retain issue coverage;
- one active implementation phase remains explicit;
- closed implementation is not represented as unearned product validation;
- USB remains blocked until every base gate passes;
- public summaries remain understandable and evidence-aligned;
- removed work includes a recorded reason;
- superseded issues link to their replacements.
