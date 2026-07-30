# Roadmap bootstrap

GitHub Issues are currently disabled for this repository. The repository owner must enable **Settings → General → Features → Issues** before the issue roadmap can be materialized.

The first roadmap-governance PR deliberately does not create labels, milestones, issues, or dependency links while Issues are disabled.

After Issues are enabled and the governance PR is merged, the next focused roadmap-tooling PR will:

1. add the reviewed label and milestone definitions;
2. add a schema-versioned bootstrap seed derived from `docs/roadmap/public-roadmap-governance.md`;
3. create or verify labels and milestones;
4. create the initial roadmap issues with stable hidden IDs;
5. add GitHub `blocked by` dependency links;
6. validate B01–B20 and U01–U04 coverage;
7. generate the static public roadmap snapshot;
8. generate the compact agent index and bounded per-issue context command;
9. add freshness, fallback, stale-data, and partial-graph protections;
10. stop treating the bootstrap seed as authoritative once the issue graph exists.

## Truth after bootstrap

```text
GitHub Issues and dependencies     planned outcomes
agents/task-dag.json               current work authorization
acceptance ledger and evidence     validated product claims
website/agent snapshots            generated caches
```

The bootstrap process must be safe to check repeatedly, but it must not overwrite issue bodies, state, or dependencies that agents have legitimately refined after bootstrap.
