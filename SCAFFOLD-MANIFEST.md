# Scaffold manifest

## Product boundary

Initial static validation and explicitly unrun authorized/hardware gates are recorded in `VALIDATION.md`.

This repository prepares one Android modular monolith that preserves Podroid's
APK-native QEMU process path while adding profile-driven VM deployment, a
durable supervisor, embedded host mesh, guest mesh/bootstrap, and a typed Host
API. Guest configuration remains ordinary SSH/Ansible work. USB AOA networking
is a separately gated MVP+ track.

## Repository roots

| Root | Purpose | Architectural role |
|---|---|---|
| `android/upstream/` | pinned Podroid import metadata | upstream island |
| `android/modules/node-model/` | values and state types | onion domain |
| `android/modules/node-core/` | ports, plans, use cases | onion application |
| `android/modules/node-store/` | Room journal/current state | persistence adapter |
| `android/modules/runtime-qemu/` | typed QEMU compiler/process/QMP | runtime adapter |
| `android/modules/mesh-tailscale/` | Android-aware libtailscale/VpnService | mesh adapter |
| `android/modules/control-api/` | typed Ktor Host API | inbound adapter |
| `android/modules/node-shell/` | Android lifecycle/composition | composition root |
| `android/modules/test-support/` | deterministic fakes | test-only adapter |
| `control/` | schemas and OpenAPI | stable external contracts |
| `profiles/` | Alpine, Ubuntu, K3s-lab profiles/init | VM-profile boundary |
| `controller/mvp-cli/` | disposable Python API/SSH client | MVP test client |
| `lab/headscale/` | pinned disposable coordination lab | test infrastructure |
| `tests/` | contracts, lifecycle, network, guest, device, E2E | QA evidence |
| `agents/` | DAG, compact packets, goal handoff | agent orchestration |
| `tools/` | bootstrap, context, worktree, CI, provenance | development product |
| `hostd/` | future Linux/SBC/WSL seam | post-Android placeholder |
| `usb-link/` | design-only base state | MVP+ placeholder |

## Architectural styles and their locations

- **Modular monolith:** all Android modules are compiled into one APK.
- **Onion/ports and adapters:** `node-model` and `node-core` point inward;
  platform modules implement their ports.
- **Reconciler:** desired generation + observed facts produce persistable steps.
- **Event-driven observations:** QMP, mesh, lifecycle, storage, and thermal events
  wake one authoritative supervisor actor; events are not independent writers.
- **Current state + operation journal:** Room stores current state and side-effect
  steps; this is deliberately not event sourcing.
- **Profile-driven virtualization:** boot, disks, initialization, and
  qualification are data; raw host argv remains internal knowledge only.

## Classification

- Committed architecture is recorded in `docs/architecture/classification.md`
  and ADRs.
- Replaceable adopted tools sit behind explicit ports.
- MVP hacks have expiry criteria and use `TODO(MVP-HARDENING, Txx)` comments.
- Debug/test-only facilities are checked out of the release surface.
- USB executable work is blocked by `tools/ci/check-mvp-plus-gate.py`.

## Agent-native controls

- Nested `AGENTS.md` files scope instructions by directory.
- `agents/tasks/Txx/context.list` prevents recursive context loading.
- `allowed-paths.txt` plus `verify-scope.py` constrain writes.
- `check-tasks.py` rejects overlapping ownership inside a parallel wave.
- Worktree helpers enforce dependency order.
- Commit trailers record exact runtime model/run/task/mode without a shared
  mutable context ledger.

## Seeded acceptance assets

- Enrollment and guest-secret schemas/examples.
- OpenAPI resource surface.
- Alpine direct-kernel qualification profile.
- Ubuntu 24.04 ARM64 UEFI/cloud-image profile.
- K3s worker prerequisite-only profile and JSON qualifier.
- Podroid QEMU invariant fixture and typed compiler tests.
- Headscale 0.28 laboratory and one-use tagged-key scripts.
- Static, JVM, Android, network, lifecycle, guest, E2E, and device test roots.

## Deliberately absent

- Podroid source itself; import it at the pinned lock.
- Live auth keys or controller configuration.
- Downloaded VM images and firmware.
- Production enrollment cryptography/TUF.
- Finished Slint controller or Linux `hostd`.
- Executable USB networking before the base gate.
