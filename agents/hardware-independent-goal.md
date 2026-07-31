# Hardware-independent development goal

## Objective

Use bounded host-side work to reduce implementation or physical-debugging ambiguity without replacing the stock-Android physical critical path. Future roadmap items are context and hypotheses until a reviewed phase transition adds a packet to `agents/task-dag.json`.

Read the durable direction in `docs/product/north-star.md`, the bounded current milestone in `GOAL.md`, and the evidence-driven order in `docs/roadmap/strategic-priorities.md`.

## Current repository truth

Current authorization must be read from `agents/task-dag.json`, not copied from this prose. At the time of this document update:

```text
F01    MERGED         canonical artifact and production profile resolution
H01    MERGED         authenticated resumable artifact upload
H02    SUPERSEDED     former combined guest boot and mesh packet
H02A   ACTIVE         canonical Ubuntu guest boot qualification
H02B   QUEUED_REVIEW  guest mesh identity and recovery qualification
H03    QUEUED_REVIEW  managed-emulator lifecycle coverage
H04    MERGED         hardened one-phone HIL evidence path
WEB04  MERGED         GitHub roadmap and compact agent index foundation
```

The strategic roadmap catalog adds queued product and platform outcomes. It does not authorize them and does not change acceptance status.

## Active phase: derive from `agents/task-dag.json`

H02A is currently the sole active task. Its bounded purpose is to prove the canonical Ubuntu profile, exact boot inputs, QMP-running state, NoCloud completion, key-only loopback SSH, guest reboot, complete QEMU stop/start, secret hygiene, evidence, and cleanup on Linux host QEMU.

The phase makes no Android, physical-device, guest-mesh, orchestrator, release, or acceptance claim.

## Stop condition

H02A is complete when its reviewed packet and real host-QEMU evidence pass. Do not extend it into a general VM laboratory, runtime supervisor, mesh testbed, cross-platform abstraction, or product release framework.

Further host-QEMU work requires either:

- a failure found in the imminent phone path that the host lab can isolate;
- a direct security/correctness defect;
- a mismatch where preflight and APK use different production contracts.

## Next product-critical work

After H02A:

1. review whether H02B still removes the next highest-value uncertainty;
2. execute the existing `tests/hil/` physical sequence using the development VM and exact target phone;
3. close the stock node substrate against one exact APK;
4. only then consider activating the smallest turnkey-cluster roadmap item justified by evidence.

The strategic expected path after the stock substrate is:

```text
MVP-01 signed provisioning capsule
  → MVP-02 real Docker Swarm worker proof
  → MVP-03 thin Slint controller
  → MVP-04 Nix/OpenTofu composition
  → MVP-05 unattended safety floor
```

This sequence is planned, not authorized.

## Phase-boundary protocol

### Start

1. Update from current `main`; run `make dev-plan` and `make validate`.
2. Refresh roadmap, pull-request, acceptance, debt, and evidence state.
3. Compare proposed work with the north star, `GOAL.md`, strategic priorities, and active issue dependencies.
4. Re-evaluate necessity, order, allowed paths, compatibility policy, and evidence limits.
5. Activate only the smallest task or genuinely path-disjoint set justified by current evidence.

### During

- Keep only current-phase tasks in `agents/task-dag.json`.
- Keep the active GitHub issue label synchronized with the DAG.
- Update the packet and experiment record when discovery changes the real problem.
- Distinguish planned, active, review, merge-ready, merged, and evidence-qualified states.
- Do not use idle agent capacity as justification for speculative work.

### End

1. Check every task and phase-exit criterion against actual outputs.
2. Run the smallest relevant test first, then the packet-required checks and applicable CI.
3. Report every required or relevant check that could not run and why.
4. Verify the work is on the assigned `agent/<TASK>-<slug>` branch/worktree and that the worktree is clean.
5. Before handoff, run `python3 tools/agents/verify-scope.py <TASK>` and resolve or report every scope violation.
6. Record implementation state and real evidence separately.
7. Record agent provenance through `tools/provenance/commit-agent.sh` for the commits being handed off.
8. Merge only the exact reviewed head and record its SHA.
9. Replan the next phase; never auto-activate the next dependency-clear issue.

## Rules

- Keep public APIs typed and preserve separate host and guest identities.
- `tests/hil/` remains the sole physical runner; host tooling and issue state cannot close physical gates.
- Do not move cluster workload state into the Host API.
- While H02A is active, Slint, Swarm, Nix/OpenTofu, patched Android, Linux/SBC/WSL, Zenoh, DDNS, QR/account enrollment, user-owned storage, and USB implementation remain unauthorized unless `agents/task-dag.json` explicitly changes through a reviewed phase transition.
- USB/AOA remains blocked until every base gate is PASS.

## Completion report

Report the exact source commit, checks, evidence class, unresolved criteria, physical limitations, roadmap disagreements, and why the next phase shape is the smallest evidence-driven choice.

Any report presented as physical evidence must also identify the exact APK digest, configured device facts, scenario, commands, and assertions. A report missing any of those fields is diagnostic context only and cannot qualify or close a physical gate.
