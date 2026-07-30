# Hardware-independent development cycle

The physical Android gates remain authoritative, but useful development can continue without a spare phone. This cycle is ordered by impact-to-effort and is intentionally limited to four parallel tasks with disjoint ownership.

## Active wave

| Task | Purpose | Why now |
|---|---|---|
| H01 | Authenticated resumable artifact upload | Removes the current inability to deliver a large VM image from a local/tailnet controller without weakening SSRF protections. |
| H02 | Host-QEMU + Headscale guest E2E | Separates Ubuntu, NoCloud, SSH, Tailscale, and image problems from Android packaging before scarce device time. |
| H03 | Managed-emulator lifecycle suite | Exercises the Android shell, Room, UI and API lifecycle with fake runtime/mesh adapters in repeatable CI. |
| H04 | Physical evidence automation | Converts a borrowed or remotely streamed device session into exact, redacted gate evidence instead of manual investigation. |

The active machine-readable graph is `agents/task-dag.json`; T00–T09 remain historical packets.

## Follow-on cycle, created only after active results

1. JSON-backed production `ProfileRegistry`.
2. True qcow2 backing-overlay semantics or an explicitly renamed copied-disk contract.
3. Project-owned source builds and provenance for QEMU, libslirp, launcher, kernel, initramfs and qualification rootfs.
4. Property/state-machine tests, parser fuzzing, dependency verification and SBOM checks.
5. Android Device Streaming or another remote-physical-device pilot using H04's collectors.

## Development rule

A follow-on refactor starts only when it removes a demonstrated blocker, reduces debugging ambiguity, or replaces a documented MVP hack whose expiry trigger has occurred. USB/AOA remains outside this cycle.
