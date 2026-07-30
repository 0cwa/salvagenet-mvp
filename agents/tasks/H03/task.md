# H03 — Managed-emulator lifecycle suite

## Status

**QUEUED FOR A LATER PHASE-START REVIEW — not active work.**

F01 is merged, but H02A is the current uncertainty. H03 may be reconsidered after H02A or earlier only if a concrete Android lifecycle blocker makes emulator infrastructure the higher-value next step.

## Provisional outcome

Potentially add deterministic emulator/instrumentation coverage for Activity, foreground Service, Room, imported enrollment, fake runtime/mesh, API, package replacement, and post-unlock reconciliation behavior.

## Phase-start review

Before activation:

1. Re-run the current JVM, Android unit, and Robolectric suites and identify lifecycle behaviors that cannot be tested adequately without an emulator.
2. Measure the remaining ambiguity after H02A and any available diagnostic HIL runs.
3. Decide whether H03 should split into:
   - a reproducible, stateless API 36 emulator harness; and
   - product lifecycle/instrumentation scenarios.
4. Remove scenarios already proved by unit/contract tests and avoid test-only product state or debug endpoints.
5. Confirm fake runtime/mesh adapters exercise real application ports and cannot enter release artifacts.
6. Revalidate that emulator evidence cannot update physical acceptance gates.
7. Decline or defer the task if setup/maintenance cost exceeds the physical-debugging ambiguity it removes.

## Acceptance criteria

This queued packet has no executable acceptance criteria yet. A future phase-start review must rewrite and approve criteria such as:

- stateless emulator creation and teardown;
- only the lifecycle behaviors that add evidence beyond existing tests;
- release-surface exclusion of fakes and fault injectors;
- explicit `emulator` evidence classification and `physicalGateEligible: false`.

## Phase-end verification

A future active packet must define its own exact checks and evidence. The following commands are provisional only:

```sh
make validate
make emulator-install
make emulator-start
make test-emulator
make emulator-stop
python3 tools/agents/verify-scope.py H03
```

## Handoff

Do not begin from this packet as written. At a later phase boundary, revise its necessity, split, dependencies, allowed paths, acceptance criteria, cost, and evidence expectations before changing implementation files.
