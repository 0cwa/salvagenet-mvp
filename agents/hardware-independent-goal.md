# Hardware-independent development goal

## Objective

Build the minimum coordination foundation needed for agent-native development and the static website without replacing the Podroid-fork MVP critical path. Work proceeds one reviewed phase at a time; future packets and issues are hypotheses until explicitly authorised.

## Repository truth

```text
F01    MERGED         canonical artifact and production profile resolution
H01    MERGED         authenticated resumable artifact upload
H02    SUPERSEDED     former combined guest boot and mesh packet
H02A   QUEUED_REVIEW  canonical Ubuntu guest boot qualification; reactivate after WEB04
H02B   QUEUED_REVIEW  guest mesh identity and recovery qualification
H03    QUEUED_REVIEW  managed-emulator lifecycle coverage
H04    MERGED         hardened one-phone HIL evidence path
WEB04  PLANNED        issue roadmap and human-aware agent index
```

PR #19 merged at `b42c35ac17793fb1621baf19905a0eacea9b3521` after full CI and accepted the Podroid-MVP alignment, roadmap truth, static-site/theme architecture, and human-aware planning contracts.

H02A remains the next product-critical task. It is paused, not superseded, for one bounded roadmap-foundation phase selected before website implementation. No H02A implementation or evidence is discarded.

## Active phase: `roadmap-foundation-1`

The sole active task is WEB04. It must:

1. create and validate the complete stable-ID roadmap seed;
2. bootstrap GitHub labels, milestones, issues, and real dependency links idempotently;
3. generate a last-known-good public snapshot and compact agent index;
4. expose bounded status, freshness, sync, and per-issue context entry points;
5. keep issue state, task authorisation, pull-request state, and acceptance evidence separate;
6. make replanning visible to humans without loading the full issue history into agent context.

The phase adds planning infrastructure only. It cannot claim Android, guest, host-QEMU, physical-device, release, website, or acceptance progress.

## Why this ordering is aligned

The user selected the task-management foundation before the website. The website must consume the same live roadmap graph used by agents rather than inventing another plan. This is a short enabling reordering, not a change to the MVP.

After WEB04, normally reactivate H02A. WEB01 may then run as a path-disjoint website task only if the live graph/index is healthy and the phase-start review confirms no ownership conflict.

## Phase-boundary protocol

### Start

1. Update from current `main`; run `make dev-plan` and `make validate`.
2. Refresh roadmap, pull-request, acceptance, and debt state.
3. Compare proposed work with `GOAL.md` and `docs/roadmap/podroid-mvp-alignment.md`.
4. Re-evaluate necessity, order, dependencies, allowed paths, compatibility policy, and evidence limits.
5. Activate only the smallest task or path-disjoint set justified by current evidence.

### During

- Keep only current-phase tasks in `agents/task-dag.json`.
- Update the packet and experiment record when discovery changes the real problem.
- Keep state changes visible in issues and the phase PR; issue labels do not grant work permission.
- Distinguish planned, active, review, merge-ready, merged, and evidence-qualified states.

### End

1. Check every task and phase-exit criterion against actual outputs.
2. Run required checks and complete applicable CI.
3. Record live bootstrap/apply and snapshot results separately from source implementation.
4. Merge the exact reviewed head and record its SHA.
5. Replan the next phase; do not auto-activate the next dependency-clear issue.

## Rules

- Keep public APIs typed and preserve separate host and guest identities.
- `tests/hil/` remains the sole physical runner; issue state or host tooling cannot close physical gates.
- H02A, H02B, H03, website pages, controller rewrites, runtime isolation, broader guest classes, and USB are out of WEB04 implementation scope.
- USB/AOA remains blocked until every base gate is PASS.

## Completion report

Report the phase entry review, exact seed/live graph counts, source hash, snapshots, context bounds, GitHub workflow/apply results, checks, drift findings, unresolved blockers, and the reason for the next phase shape.
