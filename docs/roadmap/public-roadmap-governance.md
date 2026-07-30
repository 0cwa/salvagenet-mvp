# Public issue-roadmap governance

## Purpose

The SalvageNet roadmap should be complete enough to show the intended path, small enough to understand, and flexible enough to change when implementation or testing reveals a better order.

GitHub Issues will become the roadmap source of truth after the bootstrap process creates the labelled issues, milestones, and dependency links described here.

This document defines the governance contract and the initial coverage inventory. It does not authorize implementation work.

## Four separate authorities

| Question | Authority |
|---|---|
| What direction must the project preserve? | `GOAL.md` and accepted ADRs |
| What outcomes are planned and what blocks them? | GitHub roadmap issues, milestones, and dependencies |
| What may an agent implement now? | `agents/task-dag.json` and the active task packet |
| What may the project claim as validated? | acceptance ledger and reviewed evidence |

An issue may be closed while a related acceptance gate remains `BLOCKED-HARDWARE`. A queued issue may be visible on the roadmap while no agent is authorised to work on it.

## Roadmap issue contract

Every roadmap issue has:

- the `roadmap` label;
- one milestone;
- exactly one `area:*` label;
- exactly one `kind:*` label;
- either `roadmap:public` or `roadmap:internal`;
- a stable hidden marker: `<!-- roadmap-id: <stable-id> -->`;
- a short public summary suitable for `salvage.network`;
- an observable outcome;
- finite acceptance criteria;
- explicit non-goals;
- required validation;
- linked acceptance IDs when relevant;
- a task-packet path when one exists;
- issue dependency links for hard ordering.

Agent-state labels are optional and mean:

- `agent:queued` — candidate work; not authorised;
- `agent:ready` — dependencies are clear and a packet has passed phase-start review;
- `agent:active` — current authorised implementation work;
- `agent:review` — implementation or a phase plan is under review;
- `agent:hold` — intentionally held for later re-evaluation.

Issue dependency state is derived independently. An issue can be `agent:queued` and dependency-clear without becoming authorised.

## Milestones

The initial milestone bands are:

1. **M0 — Foundation** — core Android/QEMU, artifact, evidence, and repository foundations;
2. **M0.5 — Public project surface** — static website, design system, generated status, and issue-roadmap foundation;
3. **M1 — Validated MVP** — complete one-phone Android, Linux guest, network, recovery, and durability path;
4. **M2 — Early access** — guided setup, verified downloads, first device records, tested guides, and community testing;
5. **M3 — Reliability** — thermal, storage, network, OEM lifecycle, upgrade, and device-class qualification;
6. **M4 — Platform expansion** — stronger isolation, reproducible builds, controller, Linux hosts, profiles, and adapters;
7. **MVP+ — USB physical link** — Android Open Accessory link, QEMU stream NIC, Linux TAP/NAT, and fallback.

Milestone order communicates delivery sequence. A due date is added only when the project is prepared to communicate and maintain one.

## Initial complete roadmap inventory

Stable IDs below become hidden issue markers. Issue numbers are assigned during bootstrap.

### M0 — Foundation

| Stable ID | Outcome | Initial state |
|---|---|---|
| `FND-01` | Canonical checked-in VM profiles and one strict artifact-manifest contract are the production source of truth. | Done |
| `FND-02` | A trusted controller can deliver large artifacts through bounded, authenticated, resumable, digest-verified upload. | Done |
| `FND-03` | One evidence-bound HIL runner owns physical-device scenarios and records exact device, commit, and APK identity. | Done |
| `FND-04` | Podroid upstream source, downstream patches, packaging hooks, and updates are deterministic and reviewable. | In review |

### M0.5 — Public project surface

| Stable ID | Outcome | Blocked by |
|---|---|---|
| `WEB-00` | Static-site, design-system, theme, roadmap-truth, and phase-replanning decisions are accepted. | — |
| `WEB-01` | Astro builds a component-based static shell with one token-driven CSS system and System/Light/Dark theme control. | `WEB-00` |
| `WEB-02` | All agreed user- and community-facing pages are published from shared components and honest copy. | `WEB-01` |
| `WEB-03` | Acceptance, evidence, and release data generate public status without hard-coded counts or candidate identities. | `WEB-01` |
| `WEB-04` | GitHub issues, milestones, and dependencies generate the public roadmap, last-known-good snapshot, and compact agent index. | `WEB-00` |
| `WEB-05` | Roadmap filters, guide search, setup checklist, checksum verification, evidence drawers, and restrained motion progressively enhance complete static HTML. | `WEB-01`, `WEB-02`, `WEB-04` |
| `WEB-06` | GitHub Actions validates and deploys the exact static artifact with source hashes and stale-data protection. | `WEB-02`, `WEB-03`, `WEB-04` |

### M1 — Validated MVP

| Stable ID | Outcome | Acceptance coverage | Blocked by |
|---|---|---|---|
| `GUEST-01` | Canonical Ubuntu UEFI boot, QMP, NoCloud, key-only loopback SSH, restart, and secret hygiene pass in one bounded host-QEMU run. | Preflight for B10–B12 | `FND-01`, `FND-02` |
| `GUEST-02` | One-use guest Headscale enrolment, separate identity, tailnet SSH, restart, interruption, and recovery are qualified without Android claims. | Preflight for B11–B13 | `GUEST-01` |
| `DEVICE-01` | APK-native QEMU boots on one exact ARM64 Android phone; host Headscale and authenticated Host API are reachable. | B02, B08, B09 | `GUEST-01`, `FND-03` |
| `DEVICE-02` | The controller delivers Ubuntu artifacts, applies one generation, and reaches the separately enrolled guest with ordinary SSH. | B10, B11, B12 | `DEVICE-01`, `GUEST-02` |
| `DEVICE-03` | Recovery SSH works through the host when guest mesh is unavailable. | B13 | `DEVICE-02` |
| `DEVICE-04` | Activity, service, process, reboot-after-unlock, and controller/network outage reconcile without duplicate QEMU processes. | B07, B16, B17 | `DEVICE-01`, `DEVICE-03` |
| `RELEASE-01` | Every B01–B20 gate passes against one exact source commit, APK, device record, and reviewed evidence set. | B01–B20 | `DEVICE-01` through `DEVICE-04` |

### M2 — Early access

| Stable ID | Outcome | Blocked by |
|---|---|---|
| `EA-01` | A guided local setup explains trust, permissions, profiles, progress, recovery, and current limits. | `RELEASE-01` |
| `EA-02` | First public device records bind model, Android version, build, profile, evidence, duration, thermal notes, and limitations. | `RELEASE-01`, `WEB-02`, `WEB-03` |
| `EA-03` | The downloads page publishes exact APK verification and physical-validation status. | `RELEASE-01`, `WEB-06` |
| `EA-04` | Installation, enrolment, deployment, SSH, recovery, reset, diagnostics, and removal guides identify tested builds and environments. | `RELEASE-01`, `WEB-02` |
| `EA-05` | A safe community test-day kit covers consent, battery checks, setup, evidence, redaction, and follow-up. | `EA-02`, `EA-04` |
| `EA-06` | Diagnostics and support UX explain operation state and recovery without exposing credentials or guest data. | `RELEASE-01`, `EA-04` |

### M3 — Reliability

| Stable ID | Outcome | Blocked by |
|---|---|---|
| `REL-01` | Sustained workload classes have duration, charging, temperature, throttling, and stop-policy evidence. | `RELEASE-01` |
| `REL-02` | Storage pressure, data export, reset, and uninstall behaviour are bounded and documented. | `RELEASE-01` |
| `REL-03` | Host and guest behaviour across network changes, relay paths, and Headscale interruption is qualified. | `RELEASE-01` |
| `REL-04` | Selected Android versions and OEMs have comparable lifecycle evidence. | `RELEASE-01` |
| `REL-05` | Measured memory, storage, battery, and thermal facts drive resource admission and device classes. | `REL-01`, `REL-02`, `REL-04` |
| `REL-06` | App upgrade, rollback, and runtime continuity have a documented tested path. | `RELEASE-01`, `REL-02` |

### M4 — Platform expansion

| Stable ID | Outcome | Blocked by |
|---|---|---|
| `PLAT-01` | QEMU is isolated from controller credentials through a proven process, UID, or engine-app boundary. | `RELEASE-01` |
| `PLAT-02` | QEMU, launcher, libslirp, kernel, initramfs, and profile artifacts are built from pinned source with project-owned provenance. | `RELEASE-01` |
| `PLAT-03` | A Rust controller core and Slint desktop application replace the Python test client without changing host contracts. | `RELEASE-01`, `WEB-00` |
| `PLAT-04` | Linux, SBC, and WSL hosts implement the same host API and operation semantics through a Rust service. | `RELEASE-01`, `PLAT-03` |
| `PLAT-05` | Additional ARM64 profiles pass the same contract and a real K3s worker joins, drains, leaves, and recovers under an external control plane. | `RELEASE-01`, `REL-03` |
| `PLAT-06` | A structurally different second mesh adapter validates the host-mesh port. | `RELEASE-01`, `REL-03` |
| `PLAT-07` | TUF metadata and digest-addressed OCI/HTTP transport protect project artifact distribution. | `RELEASE-01`, `REL-06` |
| `PLAT-08` | Multiple VM instances have isolated paths, identities, disks, operations, and measured admission. | `REL-05`, `PLAT-01` |

### MVP+ — USB physical link

| Stable ID | Outcome | Acceptance coverage | Blocked by |
|---|---|---|---|
| `USB-01` | Linux and Android establish a bounded, reconnectable Android Open Accessory control link. | U01 | `RELEASE-01` |
| `USB-02` | The guest receives a second QEMU NIC over the Android USB stream bridge while SLIRP remains available. | U02 | `USB-01` |
| `USB-03` | `node-linkd` provides bounded Linux TAP/NAT connectivity and reports link health. | U03 | `USB-02` |
| `USB-04` | Guest routing prefers healthy USB and returns to SLIRP after disconnect without losing recovery. | U04 | `USB-03` |

## Completeness rules

The roadmap is complete only when all of the following hold:

1. every B01–B20 and U01–U04 acceptance ID is linked from at least one roadmap issue;
2. every active task packet maps to exactly one roadmap issue;
3. every accepted post-MVP direction is represented or explicitly declined with a reason;
4. every roadmap issue has one milestone, one area, one kind, and one visibility label;
5. the dependency graph is acyclic and all dependencies point to roadmap issues;
6. no issue labelled `agent:active` has an unresolved dependency;
7. `agents/task-dag.json` contains only the current authorised phase;
8. public summaries do not claim validation that the acceptance ledger does not support;
9. the generated snapshot records source time, source hash, and fallback state;
10. queued issues are re-evaluated before each new phase instead of being activated automatically.

## Phase-boundary replanning

Agents are expected to reshape the roadmap when evidence changes the best path.

At the end of each development phase and before the next phase begins:

1. refresh the issue graph and acceptance status;
2. inspect the completed result, unresolved uncertainty, and current critical path;
3. verify that each queued issue is still necessary and correctly scoped;
4. split issues that contain more than one independently verifiable outcome;
5. merge issues whose boundaries proved artificial;
6. reorder dependencies when implementation evidence changes the safest sequence;
7. defer or remove work whose premise no longer holds;
8. update affected public summaries, acceptance links, task-packet paths, and non-goals;
9. record a short planning rationale in the phase-transition PR;
10. activate only the smallest next task or set of path-disjoint tasks that resolves the next uncertainty.

A replan may change issue structure. It may not silently weaken `GOAL.md`, an accepted ADR, or an acceptance gate. Those changes require their own explicit reviewed decision.

## Bootstrap and steady state

The initial issue inventory is bootstrapped from a reviewed seed so labels, milestones, stable IDs, issue bodies, and dependency links are created consistently.

After bootstrap:

- GitHub Issues are authoritative;
- the seed becomes historical bootstrap input and must not overwrite edited issues;
- the website and agent tools consume generated snapshots;
- full issue bodies and comments are fetched only for a selected issue, never as default orchestrator context;
- network failures use a recent complete last-known-good snapshot;
- malformed roadmap data fails validation instead of being hidden by a stale snapshot.
