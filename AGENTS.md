# Repository instructions

## Read order

1. Read `docs/product/north-star.md` for durable SalvageNet direction.
2. Read `GOAL.md` for the bounded current stock-Android/QEMU milestone.
3. Read `agents/task-dag.json` for the sole active phase and `agents/task-registry.json` for status/provenance.
4. Read the active packet under `agents/tasks/<TASK>/task.md`; queued or merged packets are not work authorization.
5. Read `docs/roadmap/strategic-priorities.md` when planning, reviewing a phase boundary, or changing roadmap scope. It is not implementation authorization.
6. For hardware-independent orchestration, read `agents/hardware-independent-goal.md`.
7. For physical validation, read `agents/device-validation-goal.md` and `tests/hil/AGENTS.md`; do not invent another physical runner.
8. For roadmap or website planning, read `docs/roadmap/public-roadmap-governance.md`, `docs/roadmap/podroid-mvp-alignment.md`, and ADR-012 before proposing state or public claims.
9. Run `python3 tools/agents/context-pack.py <TASK>` and read only that pack plus applicable nested `AGENTS.md` files.
10. Do not recursively read `docs/`; use `docs/INDEX.md` when more context is necessary.

## Direction, roadmap, authorization, and evidence

These are separate authorities:

- `docs/product/north-star.md` and accepted product/architecture ADRs define durable SalvageNet direction.
- `GOAL.md` defines the current bounded milestone and may deliberately exclude accepted later outcomes.
- GitHub roadmap issues, milestones, and dependency links define planned outcomes and ordering after roadmap apply.
- `.github/roadmap/seed.v1.json` is first-bootstrap provenance; `.github/roadmap/expansion.v1.json` and later reviewed catalog generations add accepted outcomes without rewriting that provenance.
- `agents/task-dag.json` and the active packet define current implementation authorization.
- The acceptance ledger and reviewed evidence define validated product claims.
- Closing an implementation issue does not close an acceptance gate.
- A visible or dependency-clear roadmap issue is not work authorization unless it is in the active DAG with a reviewed packet.
- Generated roadmap and website snapshots are caches/publication inputs, not independent authorities.
- Do not load the full roadmap, every issue body, or issue comments into normal orchestrator context. Use the compact generated index and a bounded per-issue context pack.

The strategic roadmap does not authorize Slint, Swarm, Nix/OpenTofu, patched Android, Linux/SBC/WSL, Zenoh, DDNS, QR/account, storage, or USB implementation while H02A remains the active task.

## Phase-boundary rules

- At phase start, verify current `main`, run `make dev-plan` and `make validate`, then re-evaluate task necessity, prerequisites, dependencies, allowed paths, acceptance criteria, evidence limits, compatibility policy, and alignment with the north star, current milestone, and strategic priorities.
- Refresh and reconcile roadmap issues before activating the next phase. Split, merge, reorder, defer, remove, or rewrite queued issues when evidence changes the safest sequence.
- Preserve coverage of durable product directions and B01–B20/U01–U04 while replanning. A change to the north star, `GOAL.md`, an accepted ADR, or an acceptance criterion requires explicit review at the appropriate authority.
- Keep only current-phase tasks in `agents/task-dag.json`. Retain merged and queued packets in the registry for provenance.
- During implementation, update the task packet and experiment record when discovery changes the real problem.
- At phase end, check every task acceptance criterion and phase exit criterion against code, tests, package artifacts, and evidence before activating the next phase.
- Merge the exact tested head, record the merge SHA, then revise, split, remove, reorder, or activate queued tasks from the result.
- Prefer a physical or integration experiment over another abstraction when it can answer the current uncertainty more directly.
- The presence of unused agent capacity is not reason to activate speculative work.

## Development rules

- The current Android implementation is a modular monolith. Keep each change inside the task's allowed paths unless the task explicitly grants integration ownership.
- The domain/application center must not import Android, QEMU, Tailscale, Ktor, Room, Headscale, or Podroid types.
- Prefer new code in `android/modules/` beside Podroid. Modify `android/podroid/` only for a narrow composition/packaging hook or an explicitly assigned migration.
- Preserve Podroid's executable-in-`nativeLibraryDir` QEMU launch, dedicated spawn/reap thread, launcher lifetime behavior, Unix sockets, and diagnostic learnings until physical acceptance proves a replacement.
- Public configuration and APIs must use typed fields. Never expose raw QEMU arguments, raw kernel arguments, raw QMP, arbitrary shell strings, or arbitrary host file paths.
- One VM is the current milestone limit.
- USB networking is MVP+; do not start it while any base-milestone gate is incomplete.
- Kotlin/Compose/Hilt/Python/Ktor/Room are current MVP implementations, not permission to couple permanent contracts to them or preclude later Slint/Rust/shared-controller ADRs.
- The common provisioning layer must not recreate Kubernetes, Nomad, Docker/Swarm, Nix, OpenTofu, Ansible, SSH, or workload schemas. Preserve native configuration and official agents.
- Do not generalize the VM API during H02A or before physical validation unless a reviewed blocker requires it. PLAT-16 owns the later additive execution-environment contract.
- Keep code simple. Add `TODO(MVP-HARDENING, <task-id>)` only for a specific deferred refinement with an expiry trigger.

## Alpha compatibility policy

- This repository is unreleased alpha. Breaking changes to internal storage, development configuration, schemas, and unpublished APIs are allowed by default.
- Prefer one clean current representation and reset or re-provision development state. Do not preserve obsolete formats merely because they existed on an unmerged branch, in a test fixture, or in an unused development build.
- Do not add migration, fallback, dual-read, legacy parsing, or compatibility branches without explicit task authorization and evidence of real deployed state that must be preserved.
- An authorized compatibility path must name the preserved population, why reset is unacceptable, the compatibility window, tests, and a deletion trigger.
- Isolate authorized compatibility code in a dedicated migration or compatibility adapter. Canonical readers, writers, domain models, and runtime paths must not understand obsolete representations.
- Current packaging adapters are not automatically legacy compatibility. Name them for the active boundary they serve and keep their scope explicit.

## Roadmap catalog rules

- The original seed remains immutable first-bootstrap provenance.
- Add later accepted catalog generations through a reviewed expansion file and compose them through `tools/roadmap/catalog.py`.
- Catalog validation must derive item and milestone cardinality from reviewed data rather than hard-code the first bootstrap forever.
- Applying a catalog generation creates missing milestones, issues, labels, and dependency links; it must not silently overwrite legitimate live issue refinements.
- Keep issue state/labels synchronized with `agents/task-dag.json`; the DAG is the authorization source and generated projections must report disagreements fail-closed.
- New strategic outcomes default to queued or hold. Only the reviewed phase transition changes the active DAG and active issue label.

## Public website rules

- The website is statically generated and component-based.
- Public claims come from generated project data and reviewed evidence; never hard-code gate counts, candidate identity, active roadmap state, or device support.
- Default theme follows the visitor's system preference. A visible control offers System, Light, and Dark, with only an explicit local override persisted.
- All pages remain useful without JavaScript. Browser-side GitHub API calls are prohibited.
- Use the shared design-system tokens and global CSS layers; do not create page-local brand systems.

## Hardware-in-the-loop rules

- `tests/hil/` is the sole physical-device scenario implementation. Existing `tests/device/` and `tests/e2e/` scripts are compatibility wrappers.
- Use only the exact ADB serial in `.local/hil.json`; never auto-select the first connected phone.
- Changes under `runtime-qemu` should run `hil-smoke` when an authorized configured phone is available.
- Changes under `mesh-tailscale`, `control-api`, profiles, artifact consumption, or guest bootstrap should run `hil-mvp` when the phase reaches physical validation.
- Changes to supervisor lifecycle, persistence, or reconciliation should run `hil-resilience`.
- A physical check may be reported `BLOCKED-HARDWARE` only after `hil-doctor` or the relevant scenario exits 77 and records the missing prerequisite.
- A fake, emulator, host-QEMU, package build, code review, manual assertion, or roadmap issue does not close a physical gate.
- Do not add test-owned product state or a debug endpoint when observation is available through the real Host API, ADB, Headscale, diagnostics, QMP-backed state, or SSH.

## Verification

- Run the smallest relevant test first, then the task packet's required checks.
- Before handing off a registered task, run `python3 tools/agents/verify-scope.py <TASK>`.
- Report tests that could not run, especially physical-device, VPN-permission, reboot, storage-pressure, or root-authorized checks.
- Physical evidence must identify the source commit, APK digest, configured device facts, scenario, commands, and assertions.
- Strategic roadmap/catalog changes must run catalog validation, roadmap unit tests, reference checks, context generation, and a dry-run/apply review appropriate to the phase.

## Git and provenance

- Work on the assigned `agent/<TASK>-<slug>` branch/worktree, or a narrowly named phase-realignment branch when no implementation packet applies.
- Do not amend or rewrite another agent's commits.
- Use `tools/provenance/commit-agent.sh`; set `AGENT_MODEL`, `AGENT_RUN_ID`, and `AGENT_TASK_ID` where local workflow supports it.
- Keep commits small enough to revert independently. Generated files and source changes belong in separate commits when practical.
- Leave the worktree clean.
