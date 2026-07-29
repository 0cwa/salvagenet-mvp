# MVP supporting-requirement classification

The user-visible MVP is enrollment, host mesh, profile/image deployment, guest
mesh/SSH, and remote lifecycle. The following supporting requirements are
classified so a shortcut is never mistaken for permanent architecture.

## Core architecture — committed now

| Requirement | Why it is architectural |
|---|---|
| Separate Android-host and VM-guest identities | Recovery must survive a broken guest. |
| Desired/observed reconciliation | Remote retries and controller outages must not redefine state. |
| Durable operation boundary | External side effects need persisted intent and observation. |
| Typed profile and Host API | Imported configuration cannot become arbitrary execution. |
| System/data ownership separation | Runtime replacement must not imply data deletion. |
| Adapter-owned secrets | Domain state stores references/status, not Headscale admin keys or raw adapter state. |
| One authoritative Android supervisor | Activity, QMP, mesh, and receivers report events; they do not race as writers. |
| Recovery path independent of guest mesh | A guest-enrollment failure must remain repairable. |

These commitments survive replacement of Room, Ktor, Tailscale, QEMU, or the
controller implementation.

## Adopted, required for MVP, but replaceable

| First implementation | Port/boundary | Replacement trigger |
|---|---|---|
| Room/SQLite operation journal | `OperationRepository` | Direct SQL/shared implementation is clearly cheaper. |
| Persistent event-aware QMP client | `RuntimeBackend` internals | Another backend supplies equivalent observations. |
| `qemu-img` disk preparation | image/disk adapter | A safer compatible library/tool replaces it. |
| Digest/size image verification | artifact adapter | Public update distribution requires TUF/delegation. |
| Graceful QMP shutdown then bounded escalation | runtime adapter | Guest agent/backend-native shutdown proves better. |
| Ktor HTTPS server | Host-control server port | TLS, memory, or lifecycle qualification fails. |
| libtailscale Android integration | `HostMesh` | Maintenance or Android behavior fails acceptance. |
| Loopback recovery SSH proxy | recovery-channel port | A standard transport provides equivalent bounded recovery. |
| Resource/storage preflight | capability/policy port | Better Android/managed-device controls become available. |

These are MVP acceptance dependencies, but domain models must not import their
library types.

## MVP hacks — allowed only behind named seams

| Shortcut | Why accepted tonight | Expiry criterion |
|---|---|---|
| One active VM | Bounds RAM, thermal, storage, and lifecycle state | Base soak data supports concurrency. |
| Imported bearer capability over tailnet HTTPS | Enables vertical Host API quickly | Replace before multi-admin/production release. |
| Python polling CLI | Gives API and OpenSSH integration without controller rewrite | Host API stabilizes; build the durable controller. |
| Three checked-in trusted profiles | Proves distribution independence and K3s qualification | Remote/delegated profiles are needed. |
| Same-UID project-qualified QEMU guest | Preserves Podroid path | Strong process/UID isolation passes qualification. |
| Secure-after-first-unlock reboot | Matches stock Android constraints | Managed/patched unattended tier is implemented. |
| Headscale HTTP container laboratory | Fast local networking tests | Never graduate into deployment guidance. |

Each code shortcut must carry a concrete `TODO(MVP-HARDENING, Txx)` only when
there is actual deferred code work. The table, not a blanket “temporary” label,
provides the architectural expiry rule.

## Debug and testing only

- imported Podroid raw-QEMU argv capture and normalized golden fixtures;
- debug-only typed QEMU override fixtures used to reproduce upstream behavior;
- fake runtime, mesh, artifact store, clock, power, and failure injectors;
- disposable Headscale/Tailscale clients and test auth keys;
- ADB/LAN bypasses used to isolate failures before embedded mesh works;
- verbose console/QMP tracing with secret redaction;
- K3s qualification scripts that inspect prerequisites but never install or
  join a cluster.

CI/release-surface checks must prevent these from becoming user-controllable
production interfaces.

## MVP+ only

AOA USB framing, Linux `node-linkd`, TAP/NAT, QEMU `eth1`, and route failover are
architecturally orthogonal but executable work is blocked until every base
acceptance criterion is `PASS`. The base repository contains only the design,
AGENTS scope, test placeholder, and gate.
