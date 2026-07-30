# Hardware-independent development cycle

The physical Android gates remain authoritative, but useful development can continue without a spare phone. This cycle is ordered by impact-to-effort and deliberately separates implementation state from physical acceptance.

## Cycle status

| Task | State | Current repository truth |
|---|---|---|
| H01 | **IN PROGRESS** | A first authenticated resumable-upload implementation exists on `agent/H01-artifact-upload` at `1567b6694dd642a6606f62ec70965be4019cd88c`. Recovery, stale cleanup, HTTP conflict/not-found semantics, publication arbitration, regression coverage, and full CI remain before merge. |
| H02 | **PLANNED** | Host-QEMU + Headscale guest E2E has not started. It remains the next hardware-independent way to isolate Ubuntu, NoCloud, SSH, Tailscale, and image failures from Android packaging. |
| H03 | **PLANNED** | Managed-emulator Activity/Service/Room/API lifecycle coverage has not started. Emulator results will remain non-physical evidence. |
| H04 | **MERGED** | HIL evidence hardening landed on `main` in merge commit `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`, including per-run SSH trust, exact Headscale identity matching, explicit controller-unavailable evidence, remote ADB seams, and validated evidence promotion. |

The machine-readable cycle definition is `agents/task-dag.json`. `agents/task-registry.json` records current task state. T00–T09 remain historical packets.

## H01 continuation boundary

The upload protocol is selected and implemented; continuation work must harden it rather than replace it:

- sequential chunks, maximum 1 MiB;
- per-chunk and whole-file SHA-256;
- exact replay idempotency;
- app-private durable staging;
- digest-addressed payload publication plus one active manifest;
- controller resume from host-reported committed bytes;
- public HTTPS import remains a separate SSRF-hardened path.

The remaining H01 blockers are authoritative in `agents/tasks/H01/task.md` and the findings are recorded in `docs/research/experiments/H01.md`.

## Follow-on cycle, created only after active results

1. JSON-backed production `ProfileRegistry`.
2. True qcow2 backing-overlay semantics or an explicitly renamed copied-disk contract.
3. Project-owned source builds and provenance for QEMU, libslirp, launcher, kernel, initramfs and qualification rootfs.
4. Property/state-machine tests, parser fuzzing, dependency verification and SBOM checks.
5. Android Device Streaming or another remote-physical-device pilot using the hardened HIL runner.

## Development rule

A follow-on refactor starts only when it removes a demonstrated blocker, reduces debugging ambiguity, or replaces a documented MVP hack whose expiry trigger has occurred. USB/AOA remains outside this cycle.
