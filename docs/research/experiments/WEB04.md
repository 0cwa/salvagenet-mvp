# WEB04 — Issue roadmap and human-aware agent index

## Status

**PLANNED — active after the roadmap-foundation transition merges.** No live issue graph, bootstrap apply, snapshot, or website implementation exists yet.

## Question

Can one complete GitHub issue graph support public roadmap generation and bounded agent planning without becoming a second task-authority system, inflating normal context, or allowing issue state to masquerade as acceptance evidence?

## Baseline

- PR #19 merged at `b42c35ac17793fb1621baf19905a0eacea9b3521` and accepted the roadmap, website, theme, alignment, and human-aware planning contracts.
- GitHub Issues are enabled.
- The reviewed prose inventory exists, but the complete machine-readable seed, labels, milestones, issues, dependencies, snapshots, and commands do not.
- H02A remains the next product-critical qualification task and is paused only for this bounded foundation.
- PR #20 is draft FND-06 device-lab safety work; it is not merged or acceptance evidence.

## Hypothesis

A stable-ID seed plus idempotent GitHub bootstrap, strict graph validation, last-known-good normalized snapshots, a compact agent index, and bounded per-issue context will let agents and the public site share roadmap truth while `agents/task-dag.json` retains authorization and the acceptance ledger retains claim authority.

## Evidence limits

- Issue creation or closure does not prove implementation or acceptance.
- A dry-run does not prove mutation safety until apply and rerun are reviewed.
- A generated snapshot does not prove freshness without source hash/time and fallback state.
- This phase cannot claim Android, guest, device, release, reliability, or website progress.

## Planned result

Record exact source/schema identity, label/milestone/issue/dependency counts, live dry-run/apply/rerun results, graph/source hash, snapshot/index sizes, context limits, stale/fallback/partial-fetch tests, CI, and any disagreement among issue, task, PR, and acceptance state.
