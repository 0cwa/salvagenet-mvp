# Hardware-independent development goal

## Objective

Reduce physical-device debugging ambiguity without turning supporting test infrastructure into a second product roadmap. Work proceeds one reviewed phase at a time; future packets are hypotheses until the preceding phase has passed its exit criteria.

## Repository truth

```text
F01   MERGED         canonical artifact and production profile resolution
H01   MERGED         authenticated resumable artifact upload
H02   SUPERSEDED     former combined guest boot and mesh packet
H02A  PLANNED        canonical Ubuntu guest boot qualification
H02B  QUEUED_REVIEW  guest mesh identity and recovery qualification
H03   QUEUED_REVIEW  managed-emulator lifecycle coverage
H04   MERGED         hardened one-phone HIL evidence path
```

F01 landed at `246d551ca7e691a0319a4b30e29d6e4905cd9910`; its exact final head `31dcd75199928b7887132a1429392266388c0b60` passed GitHub Actions run `30549498423`. H01 landed at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`. H04 landed at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`.

`agents/task-dag.json` contains only the current phase. `agents/task-registry.json` retains merged, superseded, and queued packets for provenance and later review.

## Active phase: `guest-boot-1`

The sole active task is H02A. It proves the canonical Ubuntu guest path independently of guest mesh behavior:

1. canonical F01 profile and guest-init identity;
2. pinned Ubuntu and AAVMF artifact identity;
3. real UEFI/QMP boot;
4. NoCloud completion;
5. key-only loopback SSH;
6. guest reboot and complete QEMU stop/start;
7. redacted secret-residue inspection and bounded host-QEMU evidence.

The former broad H02 packet was split because guest boot and guest mesh are distinct failure domains. H02B remains queued behind a successful H02A phase-end review. H03 remains queued until emulator work is shown to reduce a remaining Android lifecycle ambiguity enough to justify its cost.

The application has no deployed pre-F01 installations, so non-Podroid artifacts simply require active manifests. No compatibility migration path is retained.

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
- Open focused PRs and distinguish implemented, tested, merge-ready, merged, host-qualified, and physically validated states.

### End of every phase

1. Check every task acceptance criterion and phase exit criterion against actual code, tests, package artifacts, and evidence.
2. Run the task checks and the full applicable CI workflow.
3. Record unavailable physical checks honestly; software and host-QEMU evidence cannot close physical gates.
4. Update merged task status with the merge SHA.
5. Re-evaluate, split, remove, reorder, or activate the next queued work only after the result is known.

## Queued hypotheses

- **H02B:** one-use guest Headscale enrollment, distinct guest identity, tailnet SSH, `tailscaled` restart, coordination interruption, and recovery. Requires H02A to pass.
- **H03:** split later into a stateless emulator harness and lifecycle scenarios only if that remains the highest-value unresolved ambiguity.
- A physical diagnostic may run whenever a device becomes available, but final MVP evidence must be rebound to one exact candidate commit and APK.

## Rules

- Keep public APIs typed and preserve separate host and guest identities.
- Never weaken public artifact URL protections; local delivery uses the authenticated upload resource.
- `tests/hil/` is the sole physical runner.
- Do not start guest mesh, qcow2 semantic changes, source-native builds, UI rewrites, controller rewrites, process isolation, or USB/AOA while H02A is active.
- USB/AOA remains blocked until every base gate is PASS.

## Completion report

Report the phase entry review, integrated commits, exact checks, evidence class, each acceptance/exit criterion result, unresolved blockers, and the reason for the next phase shape.
