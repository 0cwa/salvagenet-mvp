# Hardware-independent development goal

## Objective

Reduce physical-device debugging ambiguity without turning supporting test infrastructure into a second product roadmap. Work proceeds one reviewed phase at a time; future packets are hypotheses until the preceding phase has passed its exit criteria.

## Repository truth

```text
F01  MERGED         canonical artifact and production profile resolution
H01  MERGED         authenticated resumable artifact upload
H02  PLANNED        canonical Ubuntu guest boot qualification
H03  QUEUED_REVIEW  managed-emulator lifecycle coverage
H04  MERGED         hardened one-phone HIL evidence path
```

F01 landed at `246d551ca7e691a0319a4b30e29d6e4905cd9910`; final head `31dcd75199928b7887132a1429392266388c0b60` passed GitHub Actions run `30549498423`. H01 landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`. H04 landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`.

`agents/task-dag.json` contains only the active phase. `agents/task-registry.json` retains merged and queued packets for provenance and later review.

## Active phase: `guest-boot-1`

The sole active task is H02. It proves the canonical Ubuntu and UEFI artifact path independently of guest mesh behavior:

1. exact profile and locked artifact identity;
2. real QMP running state;
3. NoCloud/cloud-init completion;
4. key-only SSH through loopback SLIRP;
5. clean stop/start and restart;
6. bounded secret-hygiene inspection and host-QEMU evidence.

The phase entry and exit criteria are in `agents/task-dag.json`; executable task criteria are in `agents/tasks/H02/task.md`.

## Phase-boundary protocol

### Start of every phase

1. Update from current `main` and run `make dev-plan` plus `make validate`.
2. Read the current implementation and preceding phase result; do not copy a stale future packet into the DAG unchanged.
3. Re-evaluate task necessity, order, dependencies, allowed paths, acceptance criteria, evidence limits, and compatibility policy.
4. Activate only tasks whose prerequisites are already true and whose paths do not conflict.
5. Record what is explicitly out of scope and what evidence the phase cannot claim.

### During a phase

- Keep only current-phase tasks in `agents/task-dag.json`.
- Update the packet and experiment record when implementation discovery changes the real problem.
- Prefer one cohesive foundation or vertical slice over parallel speculative refactors.
- Open focused PRs and distinguish implemented, tested, merge-ready, merged, and physically validated states.
- This project is unreleased alpha. Reset disposable state rather than adding migration or dual-format production paths unless a separately authorized task proves a real compatibility obligation.

### End of every phase

1. Check every exit criterion against code, tests, package artifacts, and evidence.
2. Run task checks and the full applicable CI workflow.
3. Record unavailable physical checks honestly; software evidence cannot close physical gates.
4. Update merged task status with the merge SHA.
5. Re-evaluate, split, remove, reorder, or activate the next queued work only after the result is known.

## Queued next-phase hypotheses

- Guest mesh qualification remains queued behind successful H02 boot/SSH qualification.
- H03 remains queued for a possible split between emulator harness reproducibility and product lifecycle scenarios.
- A physical diagnostic may run when a device is available, but final MVP evidence must be rebound to the eventual exact candidate commit and APK.

## Rules

- Keep public APIs typed and preserve separate host and guest identities.
- Never weaken public artifact URL protections; local delivery uses the authenticated upload resource.
- `tests/hil/` is the sole physical runner.
- H02 must not add Headscale, guest-tailnet, emulator, Android lifecycle, UI, controller rewrite, process isolation, or USB/AOA scope.
- Compatibility code requires explicit authorization and isolation from canonical production paths.
- USB/AOA remains blocked until every base gate is PASS.

## Completion report

Report the phase entry review, integrated commits, exact checks, evidence class, each acceptance/exit criterion result, unresolved blockers, and the reason for the next phase shape.
