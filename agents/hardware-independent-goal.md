# Hardware-independent development goal

## Objective

Reduce physical-device debugging ambiguity without turning supporting test infrastructure into a second product roadmap. Work proceeds one reviewed phase at a time; future packets are hypotheses until the preceding phase has passed its exit criteria.

## Repository truth

```text
F01  PLANNED        canonical artifact and production profile resolution
H01  MERGED         authenticated resumable artifact upload
H02  QUEUED_REVIEW  host-QEMU and guest Headscale qualification
H03  QUEUED_REVIEW  managed-emulator lifecycle coverage
H04  MERGED         hardened one-phone HIL evidence path
```

H01 landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`; its validated head passed GitHub Actions run `30510377089`. H04 landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`.

`agents/task-dag.json` contains only the active phase. `agents/task-registry.json` retains merged and queued packets for provenance and later review.

## Active phase: `foundation-1`

The sole active task is F01. It removes two split sources of truth before more integration layers are added:

1. checked-in JSON profiles versus Kotlin production profile definitions;
2. strict artifact publication metadata versus independent runtime/listing parsers.

The phase entry and exit criteria are in `agents/task-dag.json`; the executable task criteria are in `agents/tasks/F01/task.md`.

## Phase-boundary protocol

### Start of every phase

1. Update from current `main` and run `make dev-plan` plus `make validate`.
2. Read the current implementation and the preceding phase result; do not copy a stale future packet into the DAG unchanged.
3. Re-evaluate task necessity, order, dependencies, allowed paths, and acceptance criteria.
4. Activate only tasks whose prerequisites are already true and whose paths do not conflict.
5. Record what is explicitly out of scope and what evidence the phase cannot claim.

### During a phase

- Keep only current-phase tasks in `agents/task-dag.json`.
- Update the packet and experiment record when implementation discovery changes the real problem.
- Prefer one cohesive foundation or vertical slice over parallel speculative refactors.
- Open focused PRs and distinguish implemented, tested, merge-ready, merged, and physically validated states.

### End of every phase

1. Check every exit criterion against code, tests, package artifacts, and evidence.
2. Run the task checks and the full applicable CI workflow.
3. Record unavailable physical checks honestly; software evidence cannot close physical gates.
4. Update merged task status with the merge SHA.
5. Re-evaluate, split, remove, reorder, or activate the next queued work only after the result is known.

## Queued next-phase hypotheses

H02 and H03 are deliberately not active. After F01:

- H02 must be reviewed for a possible split between guest boot/NoCloud/SSH/secret hygiene and guest Headscale resilience.
- H03 must be reviewed for a possible split between emulator harness reproducibility and product lifecycle scenarios.
- A physical D01 diagnostic may run when a device is available, but final MVP evidence must be rebound to the eventual exact candidate commit and APK.

## Rules

- Keep public APIs typed and preserve separate host and guest identities.
- Never weaken public artifact URL protections; local delivery uses the authenticated upload resource.
- `tests/hil/` is the sole physical runner.
- Do not start qcow2 semantic changes, source-native builds, UI rewrites, controller rewrites, process isolation, or USB/AOA while F01 is active.
- USB/AOA remains blocked until every base gate is PASS.

## Completion report

Report the phase entry review, integrated commits, exact checks, evidence class, each acceptance/exit criterion result, unresolved blockers, and the reason for the next phase shape.
