# Development and implementation roadmap

Supporting requirements are classified in `mvp-requirement-classification.md`. These tracks describe durable dependency order, not simultaneous active work. The current active phase and task are in `agents/task-dag.json` and `roadmap/hardware-independent.md`.

## Track 0 — development substrate

Repository scaffold, Podroid pin/import, tool authorization, AGENTS hierarchy, context packs, worktrees, provenance hooks, Headscale lab, acceptance ledger, one physical HIL runner, and phase-boundary status discipline.

## Track 1 — architectural seams

Domain values, ports, canonical packaged profile registry, strict artifact-manifest contract, command compiler, operation state machine, and adapter contract tests. F01 closed the profile/manifest source-of-truth split and merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910`.

## Track 2 — Podroid QEMU adaptation

Wrap the existing launch path, preserve command knowledge in snapshots, instance-scope paths, add profile resolution and disk layout, then remove hard-coded distribution logic from the runtime adapter. True qcow2 backing semantics remain deferred and must not be implied by the current copied-writable disk.

## Track 3 — durable Android host

NodeSupervisorService, Room operation journal, desired-state recovery, artifact import/upload, resource checks, and transient local UI. Lifecycle and OEM behavior remain physically open even where software tests pass.

## Track 4 — networking and control

Embedded host libtailscale, Headscale enrollment, typed Host API, temporary controller CLI, guest metadata/bootstrap, guest mesh identity, and recovery SSH tunnel. Software implementations exist; live host/guest mesh evidence remains open.

## Track 5 — deterministic preflight and physical vertical slice

H02A is the sole active preflight task: canonical Ubuntu UEFI/QMP, NoCloud, key-only loopback SSH, restart, and forbidden-material scanning under Linux host QEMU. Guest mesh qualification remains H02B and is queued behind H02A. Emulator infrastructure remains queued for a later value/cost review.

Then close the exact physical sequence: APK-native QEMU, host mesh/API, uploaded Ubuntu guest, guest SSH/mesh, recovery, process/reboot/controller-offline behavior, and one final commit/APK evidence seal.

## Track 6 — post-base hardening

Only after a demonstrated blocker or green base vertical slice: true qcow2 backing, source-built native assets, measured resource admission, targeted package extraction, stronger authentication, controller replacement, process isolation, and strategic UI/shared-core ADRs.

## Track 7 — MVP+

Only after base acceptance: AOA USB link, Linux TAP/NAT service, QEMU second NIC, and failover.
