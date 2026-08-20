# Deferred directions after the stock-node substrate

The durable product direction is `docs/product/north-star.md`. The complete planned outcomes and ordering live in the GitHub roadmap after catalog apply. This page is a concise coverage check, not an alternative roadmap.

## Turnkey cluster product proof

- signed provisioning capsule that composes native formats without a universal workload schema (`MVP-01`);
- Docker Engine Swarm-mode worker attachment on stock Android (`MVP-02`);
- thin cross-platform Slint provisioning controller (`MVP-03`);
- Nix and OpenTofu composition modules (`MVP-04`);
- minimum unattended safety and continuity floor before early access (`MVP-05`).

## Security, artifact, and contract hardening

- reviewed mTLS/principal authorization and revocation (`PLAT-09`);
- TUF and digest-addressed OCI/ORAS artifact distribution (`PLAT-07`);
- strong QEMU process/UID isolation and arbitrary-image threat model (`PLAT-01`);
- project-owned native runtime builds from pinned source (`PLAT-02`);
- additive execution-environment contract derived from QEMU and a structurally different backend (`PLAT-16`);
- multiple installed/active execution environments after measured admission (`PLAT-08`).

## Platform priority

- `my-avbroot-setup` patched-Android native system backend (`PLAT-17`);
- hardware/custom-AVB attestation trust tiers (`PLAT-18`);
- managed/Device Owner and patched reliability tiers (`PLAT-11`);
- AVF backend behind the runtime contract (`PLAT-12`);
- native ARM64 SBC host and stable-cell roles (`PLAT-19`);
- existing Linux native/container/VM/microsandbox host (`PLAT-20`);
- dedicated custom Linux appliance image (`PLAT-21`);
- Windows through WSL (`PLAT-22`);
- durable Rust controller and broader Slint application after the thin proof (`PLAT-03`/`MVP-03`).

## Orchestrator and configuration breadth

- additional Linux guest classes and a real K3s worker (`PLAT-15`, `PLAT-05`);
- Docker/Swarm broader reference provisioning and recovery recipes (`PLAT-10` after `MVP-02`);
- official Nomad client attachment (`PLAT-23`);
- generic external provisioner through SSH/Ansible/Nix/OpenTofu without a built-in workload model (`MVP-01`);
- remote signed profile repository and delegated maintainers (`PLAT-13`);
- web UI only through a local native controller bridge (`PLAT-14`).

## Networking and bootstrap

- second private-mesh provider only after a concrete implementation proves the existing port (`PLAT-06`);
- Zenoh research as an optional bootstrap/discovery/status fabric, not an overlay or desired-state replacement (`PLAT-24`);
- optional first eligible node running Headscale through public reachability, DDNS, TLS, backup, and controller rediscovery (`PLAT-25`);
- Android Open Accessory USB link, QEMU stream NIC, Linux TAP/NAT, fallback, hardening, and optional artifact transfer (`USB-01`–`USB-05`).

## Community infrastructure

- signed scoped QR invitations and account-linked device identity (`COMM-01`);
- user-owned data locality/availability policies expressed through upstream storage and placement (`COMM-02`);
- optional provider-neutral community dynamic DNS service (`COMM-03`).

## Deliberate holds

These directions are visible so current contracts do not preclude them, but they are not active until a reviewed phase transition adds a packet to `agents/task-dag.json`.
