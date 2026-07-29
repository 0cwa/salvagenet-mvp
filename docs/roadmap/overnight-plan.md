# Overnight one-agent-day plan

The estimate is a scope target, not a guarantee. Parallelism is used only where contracts and path ownership are already separated.

## Preparation before the overnight run

Human/root-authorized:

1. install/authorize tools and ADB;
2. start Headscale lab and verify phone reachability;
3. import pinned Podroid;
4. run unmodified Podroid baseline build/boot if time permits;
5. install hooks and create worktrees.

## Parallel wave 1

- **T00** — import/wire Podroid and capture baseline.
- **T01** — domain contracts, schemas, and three profiles.
- **T04** — Headscale lab and guest-init assets.

## Parallel wave 2

After T00/T01 contracts:

- **T02** — wrap/extract QEMU adapter and typed command compiler.
- **T03** — Room operation journal and NodeSupervisorService with fake runtime.
- **T05** — Android-aware libtailscale adapter with fake HostMesh tests.
- **T06** — Host API and Python MVP controller against fake use cases.

## Integration wave

- **T07** — connect import -> host mesh -> API -> profile -> QEMU -> guest bootstrap -> guest mesh -> SSH.
- **T08** — failure injection, security checks, device lifecycle, acceptance evidence.

## MVP+ wave

- **T09** only after `tools/ci/check-mvp-plus-gate.py` passes.

## Definition of a successful night

A fully end-to-end physical-device result is preferred. A valid partial result is a buildable imported fork with green contracts, QEMU compiler/profile tests, durable fake-runtime supervisor, operational Headscale lab, and narrowly documented hardware blockers. Never disguise unrun device tests as complete.
