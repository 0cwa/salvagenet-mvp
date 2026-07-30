# WEB04 — Issue roadmap and human-aware agent index

## Status

**PLANNED — phase-start review complete; implementation not started.** This task becomes active only after the roadmap-foundation transition PR merges.

## Outcome

Bootstrap the complete reviewed SalvageNet roadmap into GitHub Issues and generate the small, freshness-aware project views needed by agents and the future static website, without changing product behaviour or treating issue state as acceptance evidence.

## Phase-start review

- PR #19 merged at `b42c35ac17793fb1621baf19905a0eacea9b3521` and accepted the static-site, theme, roadmap-truth, Podroid-MVP alignment, and human-aware planning contracts.
- GitHub Issues are enabled, but no roadmap labels, milestones, stable-ID issues, dependency graph, machine-readable seed, public snapshot, or compact agent index exists yet.
- `GOAL.md` and `docs/roadmap/podroid-mvp-alignment.md` confirm that H02A and the one-phone vertical slice remain the product critical path.
- H02A implementation has not started. It is paused, not superseded, for this bounded coordination foundation and must be re-reviewed after WEB04.
- PR #20 is a draft device-lab safety refinement and must be represented as FND-06 without being treated as merged or acceptance evidence.
- The future website depends on the generated roadmap rather than maintaining a second hand-authored plan, so WEB04 precedes WEB01.
- GitHub mutations must be idempotent, stable-ID based, and visible. Bootstrap may create the reviewed initial graph but must not later overwrite legitimate issue edits.
- The live graph, not the bootstrap seed, becomes roadmap authority after a reviewed successful apply.

## Compatibility policy

None. This is unreleased planning infrastructure. Create one current schema and reset disposable local cache/snapshot state when it changes. Do not add legacy seed readers, dual snapshot formats, compatibility aliases, or silent coercion. A schema migration requires explicit authorization only after real external consumers exist, with a support window, tests, and deletion trigger.

## Acceptance criteria

- `.github/roadmap/seed.v1.json` contains every reviewed roadmap outcome, milestone, label, stable ID, public summary, area, kind, visibility, initial work state, dependencies, acceptance IDs, task/context paths, non-goals, and validation requirements.
- Seed validation rejects missing B01–B20/U01–U04 coverage, missing release-blocking debt coverage, missing accepted post-MVP directions, duplicate IDs, invalid paths, unknown dependencies, later-milestone blockers, cycles, incomplete metadata, and active-task disagreement.
- A bounded idempotent bootstrap supports explicit dry-run and apply modes, creates or verifies labels and milestones, creates issues with hidden stable IDs, and adds real GitHub `blocked by` relationships.
- Re-running bootstrap verifies existing stable-ID objects and reports drift; it does not overwrite live issue bodies, state, dependencies, or agent refinements after bootstrap.
- GitHub Actions exposes bootstrap through a manual workflow with explicit `issues: write`, minimal other permissions, exact-source checkout, dry-run default, and an intentional apply input.
- The fetched graph is complete before publication. Any partial issue or dependency fetch fails live generation rather than falsely showing work as unblocked.
- `website/data/roadmap.snapshot.v1.json` is schema-versioned, deterministic, bounded, and records generation time, newest issue update, source hash, fallback state, and milestone/item summaries without full bodies or comments.
- `agents/generated/roadmap.index.v1.json` contains only current milestone, active/ready/blocked summaries, stable IDs, issue numbers, dependencies, acceptance IDs, task paths, source hash, and generation time.
- Local cache under `.agent-cache/roadmap/` is ignored, bounded, credential-free, and stores only normalized graph/fetch metadata.
- Commands for status, freshness check, sync, and bounded per-issue context are documented and exposed through stable repository entry points.
- Per-issue context excludes comments by default and enforces file-count/byte limits; an explicit debug option may include only a bounded newest-first comment subset.
- Work state, dependency state, task authorization, pull-request state, and acceptance status remain separate and disagreements are reported instead of silently reconciled.
- The initial graph represents PR #19 as completed WEB-00, H02A as queued for reactivation under GUEST-01, PR #20 as FND-06 in review, all accepted post-MVP directions, EA-00 release compliance, and USB blocked behind RELEASE-01.
- Pure parsing, normalization, graph derivation, fallback, staleness, context bounding, seed validation, and idempotency behaviour have focused tests.
- Normal repository checks remain green. No Android/runtime/profile/API behaviour, acceptance gate, physical claim, website page, or USB implementation changes.

## Required checks

```sh
make validate
python3 tools/roadmap/validate_seed.py
python3 -m unittest discover -s tests/tools -p 'test_roadmap*.py'
python3 tools/agents/verify-scope.py WEB04
```

A live dry-run against `0cwa/salvagenet-mvp` is required before apply. Apply must run from the exact reviewed `main` source through the manual workflow, after which the generated snapshot/index are reviewed in a normal pull request.

## Phase-end verification

1. Check every seed and live-graph completeness invariant against GitHub, not only fixtures.
2. Confirm issue dependency edges are complete and the graph is acyclic.
3. Confirm issue state cannot alter the acceptance ledger and task labels cannot authorize work outside the DAG.
4. Confirm bootstrap is safe to rerun and cannot overwrite a post-bootstrap issue edit.
5. Inspect public and agent snapshots for bounded content, deterministic ordering, provenance, staleness, and secret absence.
6. Confirm H02A remained unimplemented and no website source was added.
7. Run required checks and complete applicable CI.
8. Record implemented, tested, live-dry-run, applied, snapshot-reviewed, merge-ready, and merged states separately.
9. Re-evaluate the next phase. Normally reactivate H02A and authorize WEB01 as a path-disjoint website task only if the live roadmap/index is healthy.

## Handoff

Report the exact source commit, seed/schema version, label/milestone/issue counts, dependency count, bootstrap dry-run/apply results, workflow run, source hash, snapshot/index paths and sizes, stale/fallback tests, context limits, live drift findings, all checks, and every unmet criterion. Do not claim product, Android, device, guest, release, or acceptance progress from roadmap state.
