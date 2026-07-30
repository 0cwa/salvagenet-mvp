# Roadmap bootstrap

GitHub Issues are enabled for this repository.

This governance PR deliberately defines the roadmap contract without materializing the live issue graph or committing a machine-readable bootstrap seed. Seed creation and validation, issue creation, labels, milestones, dependency links, snapshots, and agent commands remain implementation work that must enter an explicitly authorised roadmap-tooling phase.

## Next authorised roadmap-tooling phase

After this governance PR merges and a phase-boundary review authorises the roadmap task, the implementation will:

1. create and review `.github/roadmap/seed.v1.json` from `docs/roadmap/public-roadmap-governance.md`, including milestone/label definitions, visibility, issue-body fields, acceptance IDs, validation, task-packet/context paths, dependencies, and seed state;
2. validate that seed against current `main`, `GOAL.md`, `docs/roadmap/podroid-mvp-alignment.md`, current evidence, open debt, and the active phase;
3. create or verify the reviewed labels and milestones;
4. create the initial roadmap issues with stable hidden IDs;
5. materialize the required `<!-- roadmap-id: ... -->` marker for normalized proposals before adding the `roadmap` label;
6. add GitHub `blocked by` dependency links;
7. validate B01–B20, U01–U04, release-compliance, and accepted post-MVP direction coverage;
8. generate the static public roadmap snapshot;
9. generate the compact agent index and bounded per-issue context command;
10. add freshness, fallback, stale-data, and partial-graph protections;
11. stop treating the bootstrap seed as authoritative once the issue graph exists.

The roadmap/agent-management foundation is completed before website implementation begins. This ensures website status and roadmap components consume the same reviewed live graph agents use for planning.

## Seed state versus live state

The future `seed.v1.json` is reviewed initial bootstrap input. Its `seedState` values describe the planning state at the seed's review point.

The seed validator is intentionally independent of future `agents/task-dag.json` changes. During bootstrap, the tool re-reads the current DAG and task registry and applies the current `agent:*` label to the matching issue. After bootstrap, the live issues and generated steady-state index—not edits to the historical seed—track changing active work.

An issue-form submission is an unclassified proposal. It does not receive the `roadmap` label automatically. Normalization adds the hidden stable ID and required metadata before the generator can ingest it.

## Truth after bootstrap

```text
GitHub Issues and dependencies     planned outcomes
agents/task-dag.json               current work authorization
acceptance ledger and evidence     validated product claims
website/agent snapshots            generated caches
```

The bootstrap process must be safe to check repeatedly, but it must not overwrite issue bodies, state, or dependencies that agents have legitimately refined after bootstrap.
