# Research questions and closure state

Questions stay here until their required evidence is complete. Software implementation or simulation may narrow a question without closing a physical-device requirement.

| ID | Question | Current state | Remaining closure evidence |
|---|---|---|---|
| E01 | Can imported Podroid build reproducibly at the pinned commit on the prepared host? | **Software-closed.** Pinned import, Gradle build, packaging verification, and recorded hashes pass. Native inputs are still extracted from a pinned upstream release asset. | Reproducible project-owned native QEMU/kernel/rootfs build is tracked separately in the debt register. |
| E02 | Can sibling Android modules be wired with minimal Podroid composition changes under its current AGP/Kotlin setup? | **Closed.** All sibling modules compile and the application packages them through the narrow composition seam. | Re-run on every Podroid upstream sync. |
| E03 | Does Ktor CIO satisfy Android lifecycle, TLS, tailnet binding, and memory needs? | **Software-qualified; hardware open.** TLS/auth/API tests pass. | B09: reach the live listener through the embedded host mesh and measure lifecycle/memory on device. |
| E04 | Which minimal official Tailscale Android files must be adapted for headless host operation? | **Implementation selected; hardware open.** The pinned Android-aware libtailscale/VpnService adapter builds and passes unit tests. | B08: Headscale join, restart, network transition, and VPN-permission evidence on device. |
| E05 | Does guest Tailscale enroll reliably through QEMU SLIRP while host Tailscale is active? | **Open.** | B11–B12: direct/relay/reconnect matrix on the physical vertical slice after F01 makes the packaged profile authoritative. |
| E06 | Which UEFI/profile inputs boot the pinned Ubuntu ARM64 image under Android QEMU? | **Profile software-qualified; production-source and device boot open.** Checked-in JSON and host/profile tests pass, but Android currently mirrors profile definitions in Kotlin. | F01: packaged JSON becomes the production source. Then B10–B12 require repeated Android QEMU UEFI boot, initialization, and guest access. |
| E07 | How should cloud-init obtain/delete one-use guest enrollment secrets without persistence leakage? | **Software-qualified; disk inspection open.** Bound bootstrap, deletion, redaction, and recovery tests pass. | Inspect a real guest disk, cloud-init logs, Android diagnostics, and failure/retry paths on the exact packaged profile. |
| E08 | Can QEMU graceful shutdown be observed reliably through QMP with qualified profiles? | **Software-closed.** QMP greeting/capability/status and bounded graceful-stop/force escalation are tested. | Confirm both qualified profiles on device while closing B14/B02. |
| E09 | What foreground-service restart behavior is achievable across target OEM/device? | **Open.** | B07, B16, and B17 on at least the primary device; broader OEM claims require the Android matrix. |
| E10 | Can QEMU be isolated under another UID/process while retaining file-descriptor access? | **Deferred post-MVP.** | Isolation prototype before claiming hostile arbitrary-image support. |
| E11 | Can AOA stream networking sustain useful throughput and reconnect? | **Blocked until base MVP.** | USB/AOA lab only after every B gate passes. |

F00 records the planning and source-of-truth audit. F01 is an implementation foundation, not a physical research closure; its phase-end review must update this table if it changes the remaining live questions.
