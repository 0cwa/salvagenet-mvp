# Feature and dependency classification

This classification prevents MVP shortcuts from becoming accidental architecture.

## A. Core architecture — committed

These choices define the product and may be changed only by ADR:

| Commitment | Meaning |
|---|---|
| Modular monolith | One Android application with compile-time modules and one authoritative supervisor. |
| Onion dependency direction | Domain/application code imports no Android, Podroid, QEMU, Tailscale, Room, Ktor, or Headscale types. |
| Reconciliation | Desired generations and observed facts drive idempotent plans. |
| Durable operation journal | External side effects are bracketed by persisted intent and observation. |
| Podroid QEMU process model | Preserve APK-native executable packaging, launcher lifetime behavior, dedicated spawn/reap thread, Unix sockets, and diagnostics. |
| Typed QEMU command compiler | Raw arguments are retained as knowledge/fixtures, but public APIs accept only typed fields. |
| Profile-driven VM | Distribution, boot mode, disks, initialization, and qualification are data/profile concerns. |
| Separate host and guest identity | A broken guest cannot remove the node recovery path. |
| Host API versus guest SSH | VM lifecycle/image operations use the Host API; guest provisioning uses OpenSSH. |
| System/data separation | Resetting a system layer does not implicitly erase designated persistent data. |
| One active VM | Explicit MVP product constraint with a future-compatible instance ID. |
| USB gating | USB networking cannot start until all base-MVP gates are green. |

## B. Adopted but replaceable — selected behind ports

These are the preferred first implementations, not universal domain assumptions:

| Tool | Boundary | Reconsider when |
|---|---|---|
| Kotlin/coroutines/StateFlow | Android shell and adapters | Linux or shared-domain reuse materially exceeds duplication cost. |
| Jetpack Compose | Local recovery/setup UI | A later Slint mobile client is demonstrably cheaper or cross-platform UI becomes primary. |
| Hilt | Android composition | It obstructs test setup or module extraction. |
| Room 2.8.x | `OperationRepository` adapter | SQL control, performance, or non-Android sharing requires direct SQLite. |
| Ktor CIO 3.x | `HostControlServer` adapter | Client-auth/TLS, memory, or lifecycle tests fail. |
| libtailscale from official Android source | `HostMesh` adapter | Maintenance weight is excessive or companion-client MVP proves sufficient. |
| QEMU/TCG + QMP | `RuntimeBackend` adapter | AVF or another backend passes the same contracts across target devices. |
| SLIRP | primary fallback NIC | A rootless socket/USB/mesh path proves broadly more reliable. |
| NoCloud | guest initialization adapter | A qualified image family requires Ignition or another native datasource. |
| Headscale/Tailscale | first mesh implementation | A structurally different second provider validates broader interfaces. |
| JSON Schema + JSON enrollment | import/profile boundary | Human-authored YAML becomes necessary; canonical JSON remains wire form. |

## C. MVP hacks — functional shortcuts with expiry criteria

Every hack has a named boundary and removal condition.

| Hack | Allowed scope | Expiry trigger |
|---|---|---|
| One active VM | `RuntimeInstanceId.DEFAULT` only | Base MVP stable; resource measurements support another instance. |
| Three checked-in profiles | profile registry | Remote signed profile repository is required. |
| Digest + size verification | artifact adapter | First public remote executable/profile update release; add TUF. |
| Tailnet-restricted HTTPS plus imported controller capability | authentication adapter | Before production or multi-admin release; replace with reviewed mTLS/principal model. |
| Python `phonectl` MVP | controller test client | Host API stabilizes; replace with durable Rust controller. |
| Polling operation status | controller and tests | Streaming/event UX is needed. |
| Profile-owned cloud-init scripts | trusted checked-in profiles only | Third-party profiles or delegated maintainers are accepted. |
| Trusted project-qualified guests | QEMU same-UID process | Strong QEMU process/UID isolation is implemented and tested. |
| Headscale container lab | local tests only | Never promoted to production deployment guidance. |
| Minimal Android UI hook | Podroid composition seam | Local node UI requirements stabilize. |

## D. Debug and testing only

These must not be reachable in release builds:

- raw QEMU argument replay fixtures and command snapshots;
- debug-only typed override injector used to reproduce upstream Podroid behavior;
- fake runtime, mesh, artifact, clock, and operation repositories;
- permissive laboratory Headscale ACLs;
- LAN/ADB API bypass and companion Tailscale fallback;
- forced process death and storage-fault controls;
- emulator-only lifecycle tests;
- hard-coded test enrollment values under `tests/fixtures/`;
- disposable HTTP Headscale control URL.

## E. MVP+ — blocked until base green

- Android Open Accessory USB link;
- Linux `node-linkd` TAP/NAT service;
- QEMU second NIC over stream framing;
- automatic SLIRP/USB route failover;
- USB artifact transport.

The gate is enforced by `tools/ci/check-mvp-plus-gate.py` and the acceptance ledger.
