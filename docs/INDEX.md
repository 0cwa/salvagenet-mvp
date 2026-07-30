# Documentation index

The current acceptance state is generated in `STATUS.md`. Agents should read this index, `GOAL.md`, the active task or validation goal, and only the additional pages named by that work.

## Current status

- `STATUS.md` — generated MVP gate summary and next validation sequence.

## Architecture

- `architecture/overview.md` — system shape and styles.
- `architecture/classification.md` — core, adopted, MVP-hack, test-only, and MVP+ classification.
- `architecture/module-map.md` — module ownership and dependency rules.
- `architecture/layers-and-events.md` — onion layers, reconciliation, events, and side effects.
- `architecture/qemu-command-knowledge.md` — preserved Podroid launch knowledge and typed compiler policy.
- `architecture/vm-profiles.md` — profile model and qualified profiles.
- `architecture/networking.md` — host mesh, guest mesh, recovery, and USB boundary.
- `architecture/control-plane.md` — API versus SSH responsibilities.
- `architecture/security-boundaries.md` — trust boundaries and temporary MVP security.
- `architecture/tool-radar.md` — dependency adoption status and reconsideration triggers.
- `architecture/debt-register.md` — explicit technical debt, expiry triggers, and post-device-test refactors.
- `architecture/decisions/` — concise ADRs.

## Development

- `development/environment.md` — toolchain and reproducibility.
- `development/root-authorization-checklist.md` — user-run privileged setup.
- `development/context-engineering.md` — scoped agent context model.
- `development/git-cycle.md` — branches, worktrees, commits, integration.
- `development/provenance.md` — model/run attribution without context bloat.
- `development/overnight-operations.md` — historical initial implementation orchestration.
- `development/upstream-sync.md` — Podroid import and future synchronization.

## Testing

- `testing/strategy.md` — test environments and the small physical HIL boundary.
- `../tests/hil/README.md` — one-phone setup, scenarios, config, evidence, and exit codes.
- `testing/qa-gates.md` — exact base-MVP gates.
- `testing/headscale-lab.md` — local containerized control server.
- `testing/android-matrix.md` — later device/OS expansion matrix.
- `testing/failure-injection.md` — lifecycle and storage failure cases.
- `testing/security-checks.md` — minimum host/guest security checks.

## Roadmap

- `roadmap/overview.md` — development and implementation roadmap.
- `roadmap/overnight-plan.md` — historical one-agent-day implementation plan.
- `roadmap/dependency-dag.md` — historical implementation task dependencies.
- `roadmap/acceptance-ledger.md` — base MVP and MVP+ acceptance ledger.
- `roadmap/device-validation.md` — active H0–H3 one-phone validation sequence.
- `roadmap/post-mvp.md` — deliberately deferred work.

## Research

- `research/source-register.md` — sources and pinning rationale.
- `research/open-questions.md` — questions that require experiments.
- `research/experiment-register.md` — experiment IDs, owners, and closure evidence.
