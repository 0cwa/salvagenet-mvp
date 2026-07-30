# Roadmap bootstrap

GitHub Issues are currently disabled for this repository. The repository owner must enable **Settings → General → Features → Issues** before the issue roadmap can be materialized.

The first roadmap-governance PR deliberately does not create labels, milestones, issues, or dependency links while Issues are disabled.

After Issues are enabled and the governance PR is merged, a focused roadmap-tooling phase will:

1. review the machine-readable bootstrap seed against current `main` and the active phase;
2. create or verify the reviewed labels and milestones;
3. create the initial roadmap issues with stable hidden IDs;
4. materialize the required `<!-- roadmap-id: ... -->` marker for normalized proposals before adding the `roadmap` label;
5. add GitHub `blocked by` dependency links;
6. validate B01–B20, U01–U04, and accepted post-MVP direction coverage;
7. generate the static public roadmap snapshot;
8. generate the compact agent index and bounded per-issue context command;
9. add freshness, fallback, stale-data, and partial-graph protections;
10. stop treating the bootstrap seed as authoritative once the issue graph exists.

## Seed state versus live state

`seed.v1.json` is reviewed initial bootstrap input. Its `seedState` values describe the planning state at the seed's review point.

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
