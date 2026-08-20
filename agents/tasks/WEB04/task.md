# WEB04 — Issue roadmap and human-aware agent index

## Status

**MERGED AND APPLIED.** Implementation merged through PR #22 at `888eb7e63a3419dca3f867d6baadbe95ef8c7e1f`. The reviewed live bootstrap snapshot merged through PR #77 at `15cc2791ebc6e81860fb73ca7a58e4ad12cf5235`.

## Outcome

Bootstrap the complete reviewed SalvageNet roadmap into GitHub Issues and generate the small, freshness-aware project views needed by agents and the future static website, without changing product behaviour or treating issue state as acceptance evidence.

## Verified result

- Exact implementation head `e1b4be78beb42d35038f65ede323a51fa56e9957` passed workflow `30597378616`, including repository validation, Podroid reconstruction, JVM/domain tests, Android tests/lint, guest qualification, APK packaging, signature, and 16 KiB alignment.
- A human-visible exact-main apply was authorized through issue #23 against merge commit `888eb7e63a3419dca3f867d6baadbe95ef8c7e1f`.
- The apply created or verified 30 labels, seven milestones, 53 stable-ID issues, and 82 dependency links.
- The reviewed bootstrap seed hash is `sha256:88754754f2e7e240dfeaf2421d36d83da7b547f51ce836c986996bf701ab2e14`.
- Exact generated head `e4a4930bb22f828f0214b24249db7243eadba6f9` passed workflow `30598010253` and merged through PR #77.
- `website/data/roadmap.snapshot.v1.json` records `fallback: false`, no disagreements, and source hash `sha256:58ea35f122c38db558b533d194147230549bea3b40d1b8ee871dc11bb8daf96e`.
- `agents/generated/roadmap.index.v1.json` carries the same source hash and kept WEB04 as the sole authorized task until the separate `guest-boot-2` transition.
- GUEST-01 is issue #37 and remains bound to `agents/tasks/H02A/task.md`.
- No Android/runtime/profile/API behaviour, acceptance gate, physical claim, website page, or USB implementation changed.

## Permanent contracts

- GitHub roadmap issues and dependency links own planning state after bootstrap.
- `agents/task-dag.json` remains the sole implementation authorization source.
- Acceptance status remains owned by the acceptance ledger and reviewed evidence, never by issue closure.
- Live graph fetches must be complete before publication; structural graph failures fail closed.
- Only bounded transient transport failures may use a recent complete fallback snapshot.
- Bootstrap is stable-ID based and must not overwrite legitimate post-bootstrap issue bodies, states, dependency refinements, or agent labels.
- Public and agent projections remain bounded, freshness-aware, credential-free, and source-hashed.

## Phase-end verification

All WEB04 criteria were checked against the live GitHub graph, generated artifacts, focused tests, review findings, and complete exact-head CI. H02A remained unimplemented during WEB04. The next phase is authorized only by the separate task-DAG transition; this merged task does not authorize website or product work.

## Handoff

WEB04 is historical provenance. Use issue #31 for its public roadmap record, `.github/roadmap/bootstrap-state.v1.json` for the exact apply map, and the generated snapshot/index for reviewed cache state. Future roadmap refinements occur through live issues plus explicit snapshot refreshes, not by rerunning this task packet as active work.
