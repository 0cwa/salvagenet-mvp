# Documentation index

The current acceptance state is generated in `STATUS.md`. Current implementation authorization is always read from `../agents/task-dag.json` and the active packet; prose documents must not be treated as a competing active-task registry.

Agents should begin with the durable product direction, bounded milestone, active DAG, active packet, and only the additional pages named by that work.

## Product and current status

- `product/north-star.md` — durable SalvageNet mission, platform order, product boundary, one-config/native-format model, offline authority, HA, identity, and community direction.
- `../GOAL.md` — bounded stock-Android/QEMU substrate milestone and its exact relationship to the north star.
- `STATUS.md` — generated current gate summary and next physical validation sequence.
- `roadmap/strategic-priorities.md` — evidence-driven order from current H02A/physical testing to the turnkey cluster MVP and later platforms.
- `roadmap/podroid-mvp-alignment.md` — original Podroid-fork milestone mapping and drift alarms; interpret milestone exclusions through the north star.
- `../agents/task-dag.json` — sole active phase/task authorization.
- `../agents/tasks/H02A/task.md` — active packet while H02A remains in the DAG.

## Architecture

- `architecture/overview.md` — current Android/QEMU system shape and implementation caveats.
- `architecture/turnkey-cluster-boundary.md` — provisioning capsule, native orchestrator attachments, Nix/OpenTofu composition, networking planes, and offline behavior.
- `architecture/platform-strategy.md` — stock Android, patched Android, SBC, Linux, appliance, WSL, generic execution environments, and attestation.
- `architecture/classification.md` — core, adopted, MVP-hack, test-only, and MVP+ classification for the current implementation.
- `architecture/module-map.md` — current module ownership and dependency rules.
- `architecture/layers-and-events.md` — onion layers, reconciliation, events, and side effects.
- `architecture/qemu-command-knowledge.md` — preserved Podroid launch knowledge and typed compiler policy.
- `architecture/vm-profiles.md` — canonical packaged profile model and qualified profiles.
- `architecture/networking.md` — current host mesh, guest mesh, recovery, and USB boundary.
- `architecture/control-plane.md` — current Host API, artifact-resource, and SSH responsibilities.
- `architecture/security-boundaries.md` — current trust boundaries and temporary MVP security.
- `architecture/tool-radar.md` — dependency adoption status and reconsideration triggers.
- `architecture/debt-register.md` — open/resolved debt and expiry triggers.
- `architecture/decisions/` — concise ADRs.

## Development

- `development/environment.md` — toolchain and reproducibility.
- `development/development-loop.md` — phase start, task loop, phase end, and packet generation.
- `development/root-authorization-checklist.md` — user-run privileged setup.
- `development/context-engineering.md` — scoped agent context model.
- `development/roadmap-agent-workflow.md` — roadmap freshness, compact agent context, human-visible state, and phase replanning.
- `development/git-cycle.md` — branches, worktrees, commits, integration.
- `development/provenance.md` — model/run attribution without context bloat.
- `development/overnight-operations.md` — historical initial implementation orchestration.
- `development/upstream-sync.md` — Podroid import and future synchronization.

## Testing

- `testing/strategy.md` — test environments and the physical HIL boundary.
- `../lab/qemu/README.md` — Linux host-QEMU laboratory used by H02A.
- `../tests/hil/README.md` — one-phone setup, scenarios, configuration, evidence, and exit codes.
- `testing/qa-gates.md` — exact base-milestone gates.
- `testing/headscale-lab.md` — local containerized control server for H02B/physical work.
- `testing/android-matrix.md` — later device/OS expansion matrix.
- `testing/failure-injection.md` — lifecycle and storage failure cases.
- `testing/security-checks.md` — minimum host/guest security checks.

## Roadmap

- `roadmap/strategic-priorities.md` — accepted strategic sequence and activation rules.
- `roadmap/overview.md` — development and implementation tracks.
- `roadmap/podroid-mvp-alignment.md` — current bounded milestone mapping and drift checks.
- `roadmap/public-roadmap-governance.md` — GitHub issue-roadmap truth boundaries and phase replanning.
- `roadmap/hardware-independent.md` — active H02A phase and queued preflight/physical work.
- `roadmap/acceptance-ledger.md` — B01–B20 and U01–U04 acceptance ledger.
- `roadmap/device-validation.md` — one-phone physical validation sequence.
- `roadmap/post-mvp.md` — concise durable deferred directions.
- `roadmap/overnight-plan.md` and `roadmap/dependency-dag.md` — historical one-agent-day material.

## GitHub roadmap catalog

- `../.github/roadmap/seed.v1.json` — immutable reviewed first-bootstrap provenance.
- `../.github/roadmap/expansion.v1.json` — reviewed strategic expansion and updates to existing issue dependencies/context.
- `../tools/roadmap/catalog.py` — composes catalog generations and keeps live validation cardinality derived from reviewed data.
- GitHub issues and dependency links — live planned outcomes after apply.
- `../agents/task-dag.json` — current authorization, checked against the active issue label.
- `../website/data/roadmap.snapshot.v1.json` and `../agents/generated/roadmap.index.v1.json` — generated caches, never independent authorities.

## Public website

- `../website/README.md` — Astro static-site, global CSS, theme, component, data, and implementation structure.
- `../website/AGENTS.md` — scoped public-claim, static-first, design-system, theme, accessibility, and generated-data rules.

## Research

- `research/source-register.md` — sources and pinning rationale.
- `research/open-questions.md` — questions requiring experiments.
- `research/experiment-register.md` — experiment IDs, owners, and closure evidence.
- `research/headscale-bootstrap-ddns.md` — optional first-node Headscale, DDNS, reachability, TLS, backup, and community-provider research.
- `research/experiments/H02A.md` — current guest-boot qualification record.
- `research/experiments/H02B.md` — queued guest-mesh qualification hypothesis.

## Reading discipline

Do not recursively load all documentation into normal implementation context. Read:

1. `product/north-star.md`;
2. `../GOAL.md`;
3. `../agents/task-dag.json`;
4. the active task packet;
5. the bounded context generated for that task;
6. only the pages linked by the packet, relevant issue, or a discovered decision gap.

Queued strategic issues are context, not authorization.
