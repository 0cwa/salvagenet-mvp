# Roadmap and agent workflow

## Objective

GitHub Issues describe the complete planned path while normal agent context remains small. The roadmap is a planning graph, not standing permission to implement every visible issue.

## Separate authorities

| Concern | Authority |
|---|---|
| Durable direction | `GOAL.md` and accepted ADRs |
| Planned outcomes and dependencies | GitHub roadmap issues and milestones |
| Current implementation authorization | `agents/task-dag.json` and the active packet |
| Validated product claims | acceptance ledger and reviewed evidence |
| Website and agent projections | generated snapshots |

Issue closure never changes acceptance status. A dependency-clear issue is not automatically authorised.

## Agent start sequence

Before roadmap or implementation work:

1. read `GOAL.md` and root `AGENTS.md`;
2. run `make roadmap-status`;
3. run `make roadmap-check` when live GitHub access is available;
4. read only the assigned issue and active task packet;
5. confirm the issue is dependency-clear and the packet is present in the active DAG;
6. stop for phase review when those sources disagree.

Stable commands:

```sh
make roadmap-validate
make roadmap-status
make roadmap-sync
make roadmap-check
make roadmap-context ISSUE=WEB-04
make context TASK=WEB04
```

`make roadmap-context` writes one bounded pack under `.agent-context/roadmap/`. It excludes comments by default.

## Bootstrap and live authority

`.github/roadmap/seed.v1.json` is reviewed one-time bootstrap input. It contains stable IDs, milestones, labels, summaries, outcomes, dependencies, acceptance links, task/context paths, non-goals, and validation requirements.

The apply sequence is human-visible:

1. merge the reviewed WEB04 implementation;
2. open an issue titled `[Roadmap Apply] Bootstrap reviewed graph`;
3. add `/roadmap-apply <exact-main-sha>` as an explicit owner/member/collaborator comment;
4. the `roadmap-bootstrap` workflow verifies exact main, validates the seed, and applies labels, milestones, issues, and real `blocked by` edges;
5. it reruns in non-destructive verification mode;
6. it pushes generated bootstrap state and snapshots to an automation branch;
7. review and merge those generated files through a normal PR.

The comment trigger avoids a workflow run for every roadmap issue created during bootstrap. A manual workflow dispatch supports the same dry-run/apply boundary.

After the generated snapshot PR merges, live GitHub Issues are roadmap authority. The seed remains historical input and must not overwrite edited issue bodies, state, dependencies, or planning notes.

## Generated state

### Public snapshot

`website/data/roadmap.snapshot.v1.json` contains:

- schema version and generation time;
- repository, source hash, newest issue update, and fallback state;
- milestone summaries;
- stable ID, issue number, title, current visible public summary, URL, area, kind, work state, dependency state, blockers, task authorization, pull-request state, and acceptance links;
- explicit disagreement messages.

It excludes full issue bodies, comments, review threads, logs, attachments, credentials, and guest data.

### Compact agent index

`agents/generated/roadmap.index.v1.json` contains only current milestone, active/ready/blocked summaries, stable IDs, issue numbers, dependencies, acceptance links, task paths, task authorization, linked pull-request state, source hash, and generation time.

### Local cache

`.agent-cache/roadmap/` is ignored and contains normalized graph/fetch metadata only. It must not contain credentials or comments.

## Freshness and fallback

The fetcher records `generatedAt`, newest issue update, source hash, and fallback state.

```text
Live fetch succeeds
    validate and publish complete live data

Transient network, gateway, or rate-limit failure occurs and the complete snapshot is <= 72 hours old
    use the last-known-good snapshot and expose fallback age/reason

Transient failure occurs and the snapshot is older than 72 hours
    fail the new deployment and keep the previous site online

Structural validation or partial dependency fetch fails
    fail immediately; never publish a fallback or incomplete graph
```

Structural failures include duplicate or missing stable IDs, missing or duplicate area/kind/visibility labels, missing milestones, dependencies on non-roadmap issues, cycles, invalid task paths, and incomplete acceptance coverage.

## Work, dependency, PR, task, and acceptance state

These remain independent:

- work state: planned, queued, ready, active, review, hold, or done;
- dependency state: clear or blocked;
- task authorization: present or absent in the active DAG;
- pull-request state: open, draft, merged, or closed without merge;
- acceptance state: ledger/evidence status only.

The compact index reports disagreement instead of choosing one source silently. A merged PR may complete implementation while the related physical acceptance gate remains open.

## Human awareness

Automation may calculate and propose state, but:

- every agent-state change is visible as an issue label or phase PR;
- a phase-transition PR explains selection, reordering, deferral, split, merge, or removal;
- direction changes, accepted-ADR changes, acceptance changes, evidence deletion, release publication, and premature MVP+ work require explicit human review;
- an agent may refine issue wording and direct dependencies within its authorised phase but may not silently expand allowed paths or activate queued work;
- the visible `Public summary` section in a live issue is publication truth; a hidden bootstrap marker cannot freeze stale copy;
- comments are history, not canonical context. Important conclusions move into the issue body, packet, ADR, experiment, or evidence.

## Phase boundary

Before activating the next issue:

1. refresh roadmap, acceptance status, open debt, pull-request state, and current `main`;
2. compare the proposal with `GOAL.md` and `docs/roadmap/podroid-mvp-alignment.md`;
3. identify the smallest unresolved uncertainty;
4. re-evaluate nearby queued issues;
5. split, merge, reorder, defer, remove, or rewrite issues as evidence requires;
6. confirm B01–B20/U01–U04 and release-debt coverage;
7. create or revise the task packet and compatibility policy;
8. verify allowed paths and context limits;
9. update issue dependencies and agent labels;
10. place only the authorised phase in the DAG.

At phase end, verify issue and packet acceptance, run exact-head checks, record unavailable physical work honestly, merge the tested/reviewed head, record the merge identity, leave acceptance unchanged unless its own evidence passed, and perform a fresh phase review rather than auto-activating the next issue.

## Alignment guardrails

Agents may reshape the roadmap when:

- `GOAL.md` and accepted ADRs are not silently weakened;
- the Podroid-MVP alignment and physical critical path remain explicit;
- every base/MVP+ gate and release-blocking debt item remains represented or explicitly dispositioned;
- one active implementation phase remains visible;
- closed work is not presented as unearned validation;
- USB remains blocked until every base gate passes;
- removed or superseded work records a reason and replacement.
