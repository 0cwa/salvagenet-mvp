# Documentation index

The current acceptance state is generated in `STATUS.md`. Agents should read this index, `GOAL.md`, `agents/task-dag.json`, the sole active task packet, and only the additional pages named by that work.

## Current status

- `STATUS.md` — generated MVP gate summary and next physical validation sequence.
- `../agents/hardware-independent-goal.md` — current phase-boundary protocol and active H02A goal.
- `../agents/tasks/H02A/task.md` — sole active task, acceptance criteria, checks, and phase-end review.

## Architecture

- `architecture/overview.md` — system shape, styles, and current implementation caveats.
- `architecture/classification.md` — core, adopted, MVP-hack, test-only, and MVP+ classification.
- `architecture/module-map.md` — module ownership and dependency rules.
- `architecture/layers-and-events.md` — onion layers, reconciliation, events, and side effects.
- `architecture/qemu-command-knowledge.md` — preserved Podroid launch knowledge and typed compiler policy.
- `architecture/vm-profiles.md` — canonical packaged profile model and qualified profiles.
- `architecture/networking.md` — host mesh, guest mesh, recovery, and USB boundary.
- `architecture/control-plane.md` — API, artifact-resource, and SSH responsibilities.
- `architecture/security-boundaries.md` — trust boundaries and temporary MVP security.
- `architecture/tool-radar.md` — dependency adoption status and reconsideration triggers.
- `architecture/debt-register.md` — open/resolved debt and expiry triggers.
- `architecture/decisions/` — concise ADRs.
- `architecture/decisions/ADR-012-static-site-and-roadmap-truth.md` — accepted static-site, design-system, theme, progressive-enhancement, and roadmap-truth decision.

## Development

- `development/environment.md` — toolchain and reproducibility.
- `development/development-loop.md` — phase start, task loop, phase end, and packet generation.
- `development/root-authorization-checklist.md` — user-run privileged setup.
- `development/context-engineering.md` — scoped agent context model.
- `development/roadmap-agent-workflow.md` — roadmap freshness, compact agent context, human-visible state, and phase-replanning workflow.
- `development/git-cycle.md` — branches, worktrees, commits, integration.
- `development/provenance.md` — model/run attribution without context bloat.
- `development/overnight-operations.md` — historical initial implementation orchestration.
- `development/upstream-sync.md` — Podroid import and future synchronization.

## Testing

- `testing/strategy.md` — test environments and the small physical HIL boundary.
- `../lab/qemu/README.md` — Linux host-QEMU laboratory used by H02A.
- `../tests/hil/README.md` — one-phone setup, scenarios, config, evidence, and exit codes.
- `testing/qa-gates.md` — exact base-MVP gates.
- `testing/headscale-lab.md` — local containerized control server for later H02B/physical work.
- `testing/android-matrix.md` — later device/OS expansion matrix.
- `testing/failure-injection.md` — lifecycle and storage failure cases.
- `testing/security-checks.md` — minimum host/guest security checks.

## Roadmap

- `roadmap/overview.md` — durable development and implementation tracks.
- `roadmap/podroid-mvp-alignment.md` — original Podroid-fork MVP mapping, deliberate refinements, current critical path, and drift alarms.
- `roadmap/public-roadmap-governance.md` — complete initial issue inventory, truth boundaries, completeness rules, and dynamic phase replanning.
- `roadmap/hardware-independent.md` — F01 result, active H02A phase, and queued H02B/H03 work.
- `roadmap/overnight-plan.md` — historical one-agent-day implementation plan.
- `roadmap/dependency-dag.md` — historical implementation task dependencies.
- `roadmap/acceptance-ledger.md` — base MVP and MVP+ acceptance ledger.
- `roadmap/device-validation.md` — one-phone physical validation sequence.
- `roadmap/post-mvp.md` — deliberately deferred work.

## Public website

- `../website/README.md` — planned Astro static-site, global CSS, theme, component, data, and implementation structure.
- `../website/AGENTS.md` — scoped public-claim, static-first, design-system, theme, accessibility, and generated-data rules.

## Research

- `research/source-register.md` — sources and pinning rationale.
- `research/open-questions.md` — questions that require experiments.
- `research/experiment-register.md` — experiment IDs, owners, and closure evidence.
- `research/experiments/H02A.md` — active guest-boot qualification record.
- `research/experiments/H02B.md` — queued guest-mesh qualification hypothesis.
