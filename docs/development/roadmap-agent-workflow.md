# Roadmap and agent workflow

## Objective

GitHub Issues describe the complete planned path while normal agent context remains small. The roadmap is a planning graph, not standing permission to implement every visible issue.

The active issue label is mechanically synchronized from `agents/task-dag.json`; queued, ready, review, and hold labels remain planning state that people and reviewed phase transitions may refine.

## Separate authorities

| Concern | Authority |
|---|---|
| Durable product direction | `docs/product/north-star.md` and accepted product/architecture ADRs |
| Current bounded milestone | `GOAL.md` |
| Planned outcomes and dependencies | GitHub roadmap issues and milestones |
| Current implementation authorization | `agents/task-dag.json` and the active packet |
| Validated product claims | acceptance ledger and reviewed evidence |
| Website and agent projections | generated snapshots |

Issue closure never changes acceptance status. A dependency-clear issue is not automatically authorized.

## Agent start sequence

Before roadmap or implementation work:

1. read `docs/product/north-star.md`, `GOAL.md`, and root `AGENTS.md`;
2. read `agents/task-dag.json` and the active packet;
3. run `make roadmap-status`;
4. run `make roadmap-check` when live GitHub access is available and the current catalog generation has been applied;
5. read only the assigned issue and bounded context pack;
6. confirm the issue is dependency-clear, labelled active, and bound to a task in the active DAG;
7. stop for phase review when those sources disagree.

Stable commands:

```sh
make roadmap-validate
make roadmap-status
make roadmap-sync
make roadmap-check
make roadmap-context ISSUE=MVP-02
make context TASK=H02A
```

`make roadmap-context` writes one bounded pack under `.agent-context/roadmap/`. It excludes comments by default.

## Catalog and live authority

### Reviewed catalog generations

- `.github/roadmap/seed.v1.json` is immutable first-bootstrap provenance.
- `.github/roadmap/expansion.v1.json` adds the reviewed strategic direction without rewriting history.
- `tools/roadmap/catalog.py` composes the current reviewed catalog and derives expected issue/milestone coverage from data rather than a permanently fixed first-bootstrap count.

Later generations should be additive reviewed expansion files or an explicit schema transition.

### Exact-main apply

For a catalog generation:

1. merge the catalog/docs/tooling PR without changing the active DAG;
2. open or reuse the human-visible roadmap-apply issue;
3. add `/roadmap-apply <exact-main-sha>` as an explicit owner/member/collaborator comment;
4. the `roadmap-bootstrap` workflow verifies exact main, validates the composed catalog, and creates missing labels, milestones, issues, and `blocked by` edges;
5. it reruns in non-destructive verification mode;
6. it pushes generated bootstrap state and snapshots to an automation branch;
7. review and merge those generated files through a normal PR;
8. run strict live verification before treating the new issue set as current.

The apply operation does not overwrite legitimate visible issue wording, state, or planning notes, and it does not remove unexpected dependency edges automatically. Those changes require explicit review.

Between catalog merge and exact-main apply, strict live projection is expected to report missing reviewed issues. Do not publish a new snapshot during that bounded transition.

## Task-DAG and issue-label synchronization

`agents/task-dag.json` is the source of current implementation authorization. GitHub's `agent:active` label is a visible projection of that authority.

### Automatic workflow

`.github/workflows/roadmap-authorization.yml` runs on relevant changes to `main` and:

1. validates the composed roadmap catalog;
2. fetches live roadmap issues;
3. requires every active DAG task to map to one open roadmap issue through its task-packet marker;
4. removes stale `agent:active` labels from tasks no longer in the DAG;
5. adds `agent:active` to exactly the issues whose task packets are in the DAG;
6. preserves unrelated labels and non-active `agent:queued`, `agent:ready`, `agent:review`, or `agent:hold` planning state;
7. verifies the result in a second read-only pass.

If an open task-bound issue leaves the DAG with no reviewed non-active planning label, the synchronizer conservatively demotes it to `agent:queued`. A closed or merged task does not receive a default active/planning label.

### Fail-closed projection

The live snapshot independently reports both mismatch directions:

- an issue is labelled active but its task is absent from the DAG;
- a DAG task's issue is not labelled active.

This means mutation and validation are separate safeguards. The issue label cannot authorize work by itself, and a stale label cannot silently override the DAG.

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

Structural failures include duplicate or missing stable IDs, missing or duplicate area/kind/visibility labels, missing milestones, dependencies on non-roadmap issues, cycles, invalid task paths, incomplete accepted-direction coverage, and incomplete B/U acceptance coverage.

## Work, dependency, PR, task, and acceptance state

These remain independent:

- work state: planned, queued, ready, active, review, hold, or done;
- dependency state: clear or blocked;
- task authorization: present or absent in the active DAG;
- pull-request state: open, draft, merged, or closed without merge;
- acceptance state: ledger/evidence status only.

The compact index reports disagreement instead of choosing one source silently. A merged PR may complete implementation while the related physical acceptance gate remains open.

## Human awareness

Automation may synchronize and calculate state, but:

- every active-task change is visible in the DAG, issue label, phase PR, and generated projection;
- queued/ready/review/hold changes remain reviewed planning decisions;
- a phase-transition PR explains selection, reordering, deferral, split, merge, or removal;
- north-star changes, accepted-ADR changes, acceptance changes, evidence deletion, release publication, and premature MVP+ work require explicit human review;
- an agent may refine issue wording and direct dependencies within its authorized phase but may not silently expand allowed paths or activate queued work;
- the visible `Public summary` section in a live issue is publication truth; a hidden catalog marker cannot freeze stale copy;
- comments are history, not canonical context. Important conclusions move into the issue body, packet, ADR, experiment, or evidence.

## Phase boundary

Before activating the next issue:

1. refresh roadmap, acceptance status, open debt, pull-request state, and current `main`;
2. compare the proposal with the north star, `GOAL.md`, and strategic priorities;
3. identify the smallest unresolved uncertainty;
4. prefer a physical/integration experiment where it can answer the question directly;
5. re-evaluate nearby queued issues;
6. split, merge, reorder, defer, remove, or rewrite issues as evidence requires;
7. confirm B01–B20/U01–U04, accepted strategic directions, and release-debt coverage;
8. create or revise the task packet and compatibility policy;
9. verify allowed paths and context limits;
10. update dependencies and non-active planning labels as needed;
11. place only the authorized phase in the DAG;
12. let the authorization workflow project the active label and verify agreement.

At phase end, verify issue and packet acceptance, run exact-head checks, record unavailable physical work honestly, merge the tested/reviewed head, record the merge identity, leave acceptance unchanged unless its own evidence passed, and perform a fresh phase review rather than auto-activating the next issue.

## Alignment guardrails

Agents may reshape the roadmap when:

- the durable north star and accepted ADRs are not silently weakened;
- the bounded current milestone and physical critical path remain explicit;
- every base/MVP+ gate, accepted strategic direction, and release-blocking debt item remains represented or explicitly dispositioned;
- one active implementation phase remains visible and synchronized;
- closed work is not presented as unearned validation;
- upstream workload/configuration authority remains upstream;
- USB remains blocked until every base gate passes;
- removed or superseded work records a reason and replacement.
