# GitHub roadmap catalog and synchronization

GitHub roadmap issues and dependency links are the live planning authority. `agents/task-dag.json` is the current implementation authorization, and the acceptance ledger/evidence are validated product truth.

## Catalog generations

- `seed.v1.json` — immutable reviewed input for the first live bootstrap. It remains provenance and should not be rewritten to pretend later planning existed at bootstrap time.
- `expansion.v1.json` — reviewed strategic expansion covering the turnkey cluster proof, platform priority A–F, Nomad, Zenoh research, first-node Headscale/DDNS, community enrollment, and personal-data locality.
- `../../tools/roadmap/catalog.py` — composes the bootstrap seed and reviewed expansions, updates completeness sets, and derives live item/milestone cardinality from catalog data.
- `bootstrap-state.v1.json` — generated exact apply/source/issue map from the last reviewed apply.
- `../workflows/roadmap-bootstrap.yml` — explicit dry-run/apply workflow.
- `../../tools/roadmap/commands.py` — catalog validation and GitHub apply entry point.
- `../../tools/roadmap/sync.py` — strict live/fallback projection with reviewed acceptance and context metadata.

A later catalog generation should be a new reviewed expansion file or a clean schema-version transition. Do not rewrite a historical generation merely to avoid an additive catalog mechanism.

## Local commands

```sh
make roadmap-validate
make roadmap-bootstrap-dry-run   # requires GH_TOKEN or GITHUB_TOKEN
make roadmap-sync               # live when token exists; reviewed fallback otherwise
make roadmap-status
make roadmap-check              # requires live token after issue apply
make roadmap-context ISSUE=MVP-02
```

## Apply sequence for a catalog expansion

A roadmap expansion intentionally uses two reviewed states:

1. **Code/catalog review:** merge the catalog, tests, docs, and synchronization logic. The active DAG remains unchanged.
2. **Exact-main apply:** run the existing apply workflow against the exact merged commit to create missing milestones/issues and add missing dependency links.
3. **Generated-state review:** review and merge the updated bootstrap state, public snapshot, and agent index.
4. **Strict-live verification:** confirm the live issue set, dependencies, active issue label, DAG authorization, and generated source hash agree.

Between steps 1 and 2, strict live generation is expected to report that the new reviewed issues have not yet been materialized. Do not publish a new snapshot or claim the expansion is live until apply completes.

## Human-visible apply

After the catalog implementation PR merges, open or reuse an authorized roadmap-apply issue and add one explicit comment containing the exact current default-branch commit:

```text
/roadmap-apply <40-character-main-sha>
```

The workflow verifies the author and exact `main`, validates the composed catalog, creates missing labels/milestones/issues/dependencies idempotently, reruns without mutation, generates snapshots, and pushes a review branch.

The apply operation:

- creates missing catalog items;
- adds dependencies that are reviewed in the composed catalog but absent live;
- does not remove extra dependencies automatically;
- does not silently overwrite issue bodies, titles, state, or human refinements on existing issues;
- keeps the active issue label derived from the active DAG for newly created items;
- cannot close acceptance gates.

Existing issue wording or dependency removals require an explicit roadmap-edit review rather than being hidden in bootstrap reconciliation.

## Truth after apply

```text
North star and accepted ADRs         durable direction
GOAL.md                              current bounded milestone
GitHub issues and dependencies       planned outcomes and order
agents/task-dag.json + active packet current work authorization
acceptance ledger and evidence       validated product claims
website/agent snapshots              generated caches
```

## Synchronization invariant

The active issue label and `agents/task-dag.json` must agree. The DAG remains the implementation authority; the generated projection reports either direction of disagreement and must fail closed in strict mode.

Queued and hold issues are intentionally visible context. They are not loaded wholesale into an implementation agent's prompt and do not become active merely because their dependencies are clear.
