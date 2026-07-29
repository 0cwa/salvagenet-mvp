# Open questions requiring experiments

| ID | Question | Decision blocked | Closure evidence |
|---|---|---|---|
| E01 | Can imported Podroid build reproducibly at the pinned commit on the prepared host? | Overnight baseline | clean build logs + hashes |
| E02 | Can sibling Android modules be wired with minimal Podroid composition changes under its current AGP/Kotlin setup? | module topology | Gradle sync/unit build |
| E03 | Does Ktor CIO satisfy Android lifecycle, TLS, tailnet binding, and memory needs? | Host API adapter | physical-device API test |
| E04 | Which minimal official Tailscale Android files must be adapted for headless host operation? | mesh implementation | joined node + restart test |
| E05 | Does guest Tailscale enroll reliably through QEMU SLIRP while host Tailscale is active? | nested networking | direct/relay/reconnect matrix |
| E06 | Which UEFI firmware artifact boots the pinned Ubuntu ARM64 image under Android QEMU? | Ubuntu profile | repeatable boot + SSH |
| E07 | How should cloud-init obtain/delete one-use guest enrollment secrets without persistence leakage? | guest bootstrap | disk/log inspection |
| E08 | Can QEMU graceful shutdown be observed reliably through QMP with qualified profiles? | stop semantics | event/process/disk tests |
| E09 | What foreground-service restart behavior is achievable across target OEM/device? | reliability claim | physical lifecycle matrix |
| E10 | Can QEMU be isolated under another UID/process while retaining file-descriptor access? | hostile guest support | post-MVP prototype |
| E11 | Can AOA stream networking sustain useful throughput and reconnect? | MVP+ | USB lab report |
