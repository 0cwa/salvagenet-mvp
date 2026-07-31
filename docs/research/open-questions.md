# Research questions and closure state

Questions stay here until their required evidence is complete. Software implementation, roadmap state, website work, or simulation may narrow a question without closing a physical-device or integration requirement.

The active implementation question is determined by `agents/task-dag.json`. Strategic questions are recorded so current contracts do not preclude them; they are not work authorization.

| ID | Question | Current state | Remaining closure evidence |
|---|---|---|---|
| E01 | Can imported Podroid build reproducibly at the pinned commit on the prepared host? | **Software-closed.** Pinned import, Gradle build, packaging verification, and recorded hashes pass. Native inputs are still extracted from a pinned upstream release asset. | Reproducible project-owned native QEMU/kernel/rootfs build is tracked separately. |
| E02 | Can sibling Android modules be wired with minimal Podroid composition changes under its current AGP/Kotlin setup? | **Closed.** All sibling modules compile and the application packages them through the narrow composition seam. | Re-run on every Podroid upstream sync. |
| E03 | Does Ktor CIO satisfy Android lifecycle, TLS, tailnet binding, and memory needs? | **Software-qualified; hardware open.** TLS/auth/API tests pass. | B09: reach the live listener through the embedded host mesh and measure lifecycle/memory on device. |
| E04 | Which minimal official Tailscale Android files must be adapted for headless host operation? | **Implementation selected; hardware open.** The pinned Android-aware libtailscale/VpnService adapter builds and passes unit tests. | B08: Headscale join, restart, network transition, and VPN-permission evidence on device. |
| E05 | Does guest Tailscale enroll reliably through QEMU SLIRP while host Tailscale is active? | **Open and deliberately behind H02A.** | H02B may qualify guest identity and recovery on host QEMU; B11–B12 still require the physical host-plus-guest stack. |
| E06 | Which UEFI/profile inputs boot the pinned Ubuntu ARM64 image under the production QEMU contract? | **Production source closed; host and Android boot open.** Packaged JSON and active manifests are authoritative. | H02A real host-QEMU UEFI/QMP/NoCloud/SSH/restart evidence, then B10–B12 on Android. |
| E07 | How should cloud-init obtain and delete one-use guest enrollment secrets without persistence leakage? | **Software-qualified; real guest inspection open.** Bound bootstrap, deletion, redaction, and recovery tests pass. | H02A confirms no unrelated forbidden material; H02B and the physical guest slice inspect real redemption, retry, erasure, logs, and diagnostics. |
| E08 | Can QEMU graceful shutdown be observed reliably through QMP with qualified profiles? | **Software-closed; integration confirmation open.** QMP greeting/capability/status and bounded graceful-stop escalation are tested. | H02A stop/start and both qualified profiles on host QEMU; B14/B02 require the separate physical-device run. |
| E09 | What foreground-service restart and wake behavior is achievable across target OEM/device? | **Open.** | B07/B16/B17 on the primary phone, then MVP-05 screen-off/Doze/power/soak and the broader OEM matrix. |
| E10 | Can QEMU be isolated under another UID/process while retaining required artifact/file-descriptor access? | **Deferred.** | PLAT-01 isolation prototype before claiming hostile arbitrary-image support. |
| E11 | Can AOA stream networking sustain useful throughput and reconnect? | **Blocked until the stock base milestone.** | USB lab only after every B gate passes. |
| E12 | Can the GitHub issue graph, task DAG, and generated agent/public projections remain synchronized without becoming competing authorities? | **First bootstrap complete; strategic expansion under review.** | Merge catalog composition, apply exact-main issues/dependencies, review generated state, and verify strict live agreement while H02A remains the sole active task. |
| E13 | What is the smallest signed provisioning capsule that supports multiple platforms and upstream orchestrators without replacing native formats? | **Planned: MVP-01.** | Concrete Docker Swarm, K3s, Nomad, Nix, OpenTofu, and external-provisioner examples; signature, rollback, secret-reference, and offline-cache tests. |
| E14 | Does a stock Android/QEMU node operate as a useful Docker Engine Swarm worker under controller interruption and native drain/leave/rejoin? | **Planned: MVP-02.** | One exact physical phone/APK/capsule, real replicated service, laptop interruption, recovery, and replacement evidence. |
| E15 | What minimum unattended behavior is safe enough for early access on an old stock phone? | **Planned: MVP-05.** | Screen-off, Doze, wake, power transition, thermal stop, storage reserve, process/network/controller interruption, and bounded soak evidence. |
| E16 | Which public execution-environment fields are genuinely common to QEMU, patched-system containers, native Linux, and WSL? | **Held: PLAT-16.** | Preserve QEMU evidence, implement one structurally different backend, and derive an additive conformance contract without raw backend leakage. |
| E17 | Which maintained runtime foundation best supports the patched Android native backend? | **Held: PLAT-17.** | Compare Droidspaces/LXC/chroot/containerd/runc/Podman or other current foundations against kernel, SELinux, lifecycle, update, and threat requirements on a supported device. |
| E18 | What trust can hardware-backed Android attestation establish for vendor, custom-key locked, and unlocked patched builds? | **Held: PLAT-18.** | Fresh challenge, app identity, RootOfTrust fields, recognized AVB keys, build manifests, privacy policy, downgrade tests, and explicit lower-assurance unlocked tier. |
| E19 | Does Zenoh materially improve intermittent-controller and cell bootstrap behavior over HTTPS plus the private overlay? | **Held: PLAT-24.** | Android/Linux footprint, lifecycle, peer/client/router recovery, ACLs, query/liveliness, tailnet/USB traversal, immutable-capsule retrieval, and adopt/hold/reject ADR. |
| E20 | Can a first eligible node safely host Headscale through dynamic DNS without hiding public-reachability requirements? | **Held: PLAT-25.** | Public IPv4/IPv6 eligibility, CGNAT negative detection, DNS update, ACME, Headscale health, backup/restore, address change, controller rediscovery, and fallback tests. |
| E21 | How should signed QR invitations bind a community account, device key, attestation, consent, and limited role without permanent credentials? | **Held: COMM-01.** | OIDC/PKCE or equivalent, invitation expiry/replay, device binding, recovery, revocation, privacy, and offline/delegated issuer analysis. |
| E22 | Which user-owned storage policies can be expressed through existing orchestrator/application mechanisms without a new distributed filesystem? | **Held: COMM-02.** | Local-only, encrypted-backup, and replicated-HA proofs with explicit availability/locality trade-offs on at least one real application path. |

## Active priority

H02A remains the active bounded experiment while present in `agents/task-dag.json`. Its completion should be followed by the smallest useful physical Android scenario, not by automatic activation of E13–E22.

## Closure discipline

A roadmap issue may refine, split, merge, defer, or reject a research question. Close the question only when its named evidence exists or an ADR explicitly rejects the premise with supporting results.
