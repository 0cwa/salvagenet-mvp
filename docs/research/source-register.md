# Source register

This register records sources used to choose the scaffold and strategic roadmap. URLs are research evidence; checked-in contracts, task packets, accepted ADRs, and reviewed physical evidence remain implementation authority.

## SalvageNet and patched Android

- Current repository: `https://github.com/0cwa/salvagenet-mvp`
- AVB patch workflow: `https://github.com/0cwa/my-avbroot-setup`
- Key direction: stock APK remains priority A; the AVB workflow is an optional priority-B delivery provider for a narrowly scoped init daemon, SELinux policy, native runtime, and signed build manifest.

## Podroid

- Repository: `https://github.com/ExTV/Podroid`
- Pinned MVP import: see `android/upstream/podroid.lock`.
- Relevant upstream areas: `QemuEngine.kt`, `QmpClient.kt`, `PodroidService.kt`, `EngineHolder.kt`, `podroid-launcher.c`, `build-all.sh`, native build Dockerfile, initramfs/rootfs scripts, kernel config.
- Key learning: QEMU is an ELF executable packaged in the APK native-library directory and launched with `ProcessBuilder`; preserve launcher/thread/socket behavior through physical proof.

## Android containers and virtualization research

- Droidspaces OSS: `https://github.com/ravindu644/Droidspaces-OSS`
- Android Virtualization Framework: `https://source.android.com/docs/core/virtualization`
- Key use: evaluate concrete native-system and AVF backends only behind the proven host/runtime contracts; do not copy a general root shell or infer isolation from namespaces alone.

## Tailscale Android

- Repository: `https://github.com/tailscale/tailscale-android`
- Relevant areas: `libtailscale/interfaces.go`, Android `App.kt`, `IPNService.kt`, MDM/policy settings.
- Key learning: use Android-aware platform callbacks and `VpnService`, not generic desktop assumptions.
- Selected MVP line: Android release v1.98.2; its Tailscale core module declares Go 1.26.3. The Android repository commit remains an explicit pinning gate.

## Headscale

- Stable requirements: `https://headscale.net/stable/setup/requirements/`
- Getting started: `https://headscale.net/stable/usage/getting-started/`
- Reverse proxy caveats: `https://headscale.net/stable/ref/integration/reverse-proxy/`
- Current lab pin: see the lab configuration and lock files.
- Pre-authentication keys are used for noninteractive host/guest registration; administrative API keys stay on the controller.
- Key first-node research constraint: Headscale expects public reachability and HTTPS on TCP 443. Dynamic DNS maintains a name for an address but does not traverse CGNAT or blocked inbound ports.

## Docker and Swarm

- Docker Engine Swarm mode overview: `https://docs.docker.com/engine/swarm/`
- Joining nodes: `https://docs.docker.com/engine/swarm/join-nodes/`
- Manager quorum: `https://docs.docker.com/engine/swarm/admin_guide/`
- SwarmKit toolkit: `https://github.com/moby/swarmkit`
- Key decision: target supported Docker Engine Swarm mode, not Classic Swarm and not raw SwarmKit embedding. The first product proof uses a worker join, upstream-issued node certificate, placement, drain/leave/rejoin, and controller-offline continuity.

## Kubernetes and K3s

- K3s documentation: `https://docs.k3s.io/`
- Requirements: `https://docs.k3s.io/installation/requirements`
- Configuration: `https://docs.k3s.io/installation/configuration`
- Networking: `https://docs.k3s.io/networking/basic-network-options`
- Kubernetes node architecture: `https://kubernetes.io/docs/concepts/architecture/nodes/`
- Kubernetes cgroup v2: `https://kubernetes.io/docs/concepts/architecture/cgroups/`
- Key boundary: run the official K3s agent in a qualified Linux environment; keep Kubernetes resources and control-plane state upstream.

## Nomad

- Production requirements: `https://developer.hashicorp.com/nomad/docs/deploy/production/requirements`
- Disconnected edge services: `https://developer.hashicorp.com/nomad/tutorials/edge/schedule-edge-services`
- Job specification: `https://developer.hashicorp.com/nomad/docs/job-specification`
- License: `https://github.com/hashicorp/nomad/blob/main/LICENSE`
- Key boundary: use official Nomad client and native HCL only in a full Linux environment with required capabilities; record distribution/licensing decisions and do not import jobspecs into the Host API.

## Nix and OpenTofu

- Nix manual: `https://nixos.org/manual/nix/stable/`
- NixOS modules: `https://nixos.org/manual/nixos/stable/`
- OpenTofu documentation: `https://opentofu.org/docs/`
- Provider development: `https://opentofu.org/docs/intro/core/provider/`
- Key decision: begin with Nix and OpenTofu modules on the controller/build side, reuse existing providers, and create a first-party provider only after SalvageNet owns real remote resources.

## Zenoh

- Deployment models: `https://zenoh.io/docs/getting-started/deployment/`
- Installation/router: `https://zenoh.io/docs/getting-started/installation/`
- Access control: `https://zenoh.io/docs/manual/access-control/`
- Repository: `https://github.com/eclipse-zenoh/zenoh`
- Key research question: evaluate peer/client/router, liveliness, queries, cell gateways, and immutable-capsule retrieval as an optional bootstrap/discovery fabric. Do not treat Zenoh as the private overlay, orchestrator desired state, CRDT database, or application data plane by default.

## Android identity and attestation

- Key and ID attestation: `https://source.android.com/docs/security/features/keystore/attestation`
- Android Keystore: `https://source.android.com/docs/security/features/keystore`
- Key evidence: attestation exposes application identity and RootOfTrust fields including `verifiedBootKey`, `deviceLocked`, `verifiedBootState`, and `verifiedBootHash`. Custom-key locked and unlocked builds require distinct trust classes.

## Artifact and update trust

- OCI Distribution Specification: `https://github.com/opencontainers/distribution-spec`
- ORAS: `https://oras.land/`
- The Update Framework: `https://theupdateframework.io/`
- Sigstore Cosign: `https://docs.sigstore.dev/cosign/`
- Key direction: immutable digest identity and signed metadata protect bootable/runtime/config artifacts; transport caches need not be trusted when verification is complete.

## Configuration and protocol composition

- CUE: `https://cuelang.org/docs/`
- JSON Schema: `https://json-schema.org/`
- Protocol Buffers: `https://protobuf.dev/`
- COSE: `https://www.rfc-editor.org/rfc/rfc9052`
- CWT: `https://www.rfc-editor.org/rfc/rfc8392`
- Key direction: a small signed capsule composes native upstream configurations; do not create a universal cluster workload schema.

## Android platform

- Android Studio/command-line tools: `https://developer.android.com/studio`
- AGP compatibility: `https://developer.android.com/build/releases/agp-9-1-0-release-notes`
- NDK installation: `https://developer.android.com/studio/projects/install-ndk`
- 16 KiB pages: `https://developer.android.com/guide/practices/page-sizes`
- Foreground services: `https://developer.android.com/develop/background-work/services/fgs`
- Doze/app standby: `https://developer.android.com/training/monitoring-device-state/doze-standby`
- Direct Boot: `https://developer.android.com/privacy-and-security/direct-boot`
- Thermal API: `https://developer.android.com/games/optimize/adpf/thermal`
- Android Open Accessory: `https://source.android.com/docs/core/interaction/accessories/protocol`

## Guest/profile technologies

- QEMU ARM virt/QMP/qemu-img documentation: `https://www.qemu.org/docs/master/`
- cloud-init NoCloud: `https://cloudinit.readthedocs.io/`
- Ubuntu cloud images: `https://cloud-images.ubuntu.com/noble/current/`
- OpenSSH: `https://www.openssh.com/manual.html`

## Agent workflow

- OpenAI Codex/AGENTS guidance: official OpenAI Codex documentation and product guidance.
- The repository itself defines exact task packets, tests, provenance, roadmap authority, and bounded context requirements.
