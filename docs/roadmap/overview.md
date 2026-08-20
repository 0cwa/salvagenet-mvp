# Development and implementation roadmap

The durable product direction is `docs/product/north-star.md`. Supporting requirements for the current Android/QEMU milestone remain classified in `mvp-requirement-classification.md`. GitHub roadmap issues own planned outcomes and dependencies after catalog apply; `agents/task-dag.json` owns current authorization.

These tracks describe durable order, not simultaneous active work.

## Track 0 — development and coordination substrate

Repository scaffold, Podroid pin/import, tool authorization, scoped agent context, worktrees, provenance, Headscale lab, acceptance ledger, one physical HIL runner, phase-boundary discipline, and the live GitHub roadmap/agent-index foundation.

This track is enabling infrastructure. It cannot replace physical evidence or become a reason to delay the current device path.

## Track 1 — current architectural seams

Domain values, ports, canonical packaged profile registry, strict artifact-manifest contract, typed QEMU command compiler, operation state machine, and adapter contract tests.

The current contracts intentionally serve one QEMU VM. The later PLAT-16 item owns an additive execution-environment generalization after the stock product proof; do not perform that rewrite during H02A.

## Track 2 — Podroid QEMU adaptation

Wrap the existing launch path, preserve command knowledge in snapshots, instance-scope paths, add profile resolution and disk layout, and remove hard-coded distribution logic from the runtime adapter.

This is priority A's first backend, not the permanent definition of every SalvageNet platform.

## Track 3 — durable stock Android host

NodeSupervisorService, Room operation journal, desired-state recovery, artifact import/upload, host/guest enrollment, Android foreground lifecycle, resource checks, and local setup/recovery UI.

Physical Android/OEM behavior remains open even where software tests pass.

## Track 4 — networking and control

Embedded host libtailscale, Headscale enrollment, typed Host API, temporary Python controller, guest metadata/bootstrap, independent guest identity, ordinary SSH, and bounded recovery SSH tunnel.

Current HTTPS and Tailscale are concrete implementations. A future Zenoh bootstrap/discovery experiment is separate from the private overlay and upstream workload state.

## Track 5 — deterministic preflight and physical substrate proof

### Active

H02A/GUEST-01 qualifies canonical Ubuntu UEFI/QMP, NoCloud, key-only loopback SSH, reboot, stop/start, and forbidden-material handling on host QEMU. It is the sole authorized product task while listed in `agents/task-dag.json`.

### Next

Use the development VM and `tests/hil/` to close:

1. APK-native QEMU, host mesh, and authenticated Host API;
2. controller-delivered Ubuntu, guest identity, and ordinary SSH;
3. recovery when guest mesh is unavailable;
4. Activity/service/process/reboot/controller-offline durability;
5. one exact B01–B20 candidate seal.

H02B may run before the physical guest slice only when the H02A phase review confirms it still removes the highest-value ambiguity. It is not automatically activated.

## Track 6 — turnkey cluster MVP

After the stock substrate is validated:

1. `MVP-01`: define one signed provisioning capsule that references native runtime, overlay, and orchestrator configuration;
2. `MVP-02`: join Docker Engine Swarm mode as a real worker on the physical stock phone and prove service continuity, drain, leave, replacement, and rejoin;
3. `MVP-03`: deliver a thin Slint provisioning/diagnostics controller without moving cluster state into it;
4. `MVP-04`: provide Nix and OpenTofu modules that compile to the same capsule and native files;
5. `MVP-05`: pass the minimum screen-off/Doze/power/thermal/storage/process/network/offline-authority soak.

This is the first complete product proof. It remains smaller than Kubernetes, Nomad, patched Android, multi-platform, community, and USB work.

## Track 7 — early access and reliability

Before public APK distribution, close licensing/notices/corresponding-source requirements. Publish exact verified downloads, guided onboarding, tested recovery, and named device records only after the substrate and turnkey proof are evidence-bound.

The pre-early-access safety floor is MVP-05. Broader M3 work then qualifies:

- sustained thermal/power classes;
- storage pressure/export/reset/uninstall;
- network transitions and coordination interruption;
- OEM/Android lifecycle matrix;
- measured resource admission/device roles;
- upgrade, rollback, and runtime continuity.

## Track 8 — platform expansion in priority order

1. PLAT-16: additive execution-environment contract;
2. PLAT-17/18/11: `my-avbroot-setup` native Android backend, attestation, and managed reliability tiers;
3. PLAT-19: native SBC host/stable-cell roles;
4. PLAT-20: existing Linux service/container/VM/microsandbox modes;
5. PLAT-21: dedicated custom Linux appliance;
6. PLAT-22: Windows through WSL.

Supporting work includes QEMU isolation, project-owned native builds, artifact trust, multi-controller authorization, AVF, multiple environments, and delegated profiles.

## Track 9 — orchestrator and declarative breadth

- real K3s worker and additional guest classes;
- official Nomad client attachment;
- broader Docker/Swarm recipes after the initial proof;
- generic external provisioning through SSH/Ansible/Nix/OpenTofu;
- first-party adapters only where native join/leave/health/recovery integration is valuable.

No workload object model enters the Host API.

## Track 10 — optional bootstrap and physical links

- PLAT-24: bounded Zenoh adopt/hold/reject experiment;
- PLAT-25: first eligible node running Headscale through DDNS, public reachability, TLS, backup, and controller rediscovery;
- USB-01–USB-05: AOA control, stream NIC, TAP/NAT, fallback, hardening, and optional artifact transfer.

Dynamic DNS does not solve CGNAT. USB cannot remove SLIRP or ordinary recovery. Neither path is required for the turnkey MVP.

## Track 11 — community-owned infrastructure

After production identity and platform foundations:

- signed QR invitations and account-linked device keys;
- personal-storage locality and availability policies through upstream mechanisms;
- optional community dynamic DNS;
- explicit consent, revocation, recovery, privacy, and migration.

## Public website

The Astro website remains a static, evidence-derived public surface. It may proceed through separately authorized path-disjoint tasks, but it cannot close product or physical gates or hard-code active status.

## Simplicity rule

Use the smallest phase that resolves the next uncertainty. Do not import a parallel supervisor, VM manager, configuration authority, management transport, cluster model, storage system, or compatibility framework merely because another project provides one.

A larger mechanism must be justified by present evidence, a concrete security/correctness failure, or a product-proof blocker. Delete scope whose premise is no longer real.
