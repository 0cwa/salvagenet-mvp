> Supporting requirements are classified in [`mvp-requirement-classification.md`](mvp-requirement-classification.md).

# Development and implementation roadmap

## Track 0 — development substrate

Repository scaffold, Podroid pin/import, tool authorization, AGENTS hierarchy, context packs, worktrees, provenance hooks, Headscale lab, and acceptance ledger.

## Track 1 — architectural seams

Domain values, ports, profile schema/registry, command compiler, operation state machine, and adapter contract tests. These are built before broad UI or networking changes.

## Track 2 — Podroid QEMU adaptation

Wrap the existing launch path, preserve command knowledge in snapshots, instance-scope paths, add profile resolution and qemu-img/disk layout, then remove hard-coded Alpine logic from the runtime adapter.

## Track 3 — durable Android host

NodeSupervisorService, Room operation journal, desired-state recovery, import flow, resource checks, and transient local UI.

## Track 4 — networking and control

Embedded host libtailscale, Headscale enrollment, typed Host API, temporary controller CLI, guest metadata/bootstrap, guest mesh identity, and recovery SSH tunnel.

## Track 5 — vertical slice and QA

Ubuntu cloud-image deployment, guest SSH, K3s qualification report, process/reboot recovery, failure injection, and acceptance evidence.

## Track 6 — MVP+

Only after base acceptance: AOA USB link, Linux TAP/NAT service, QEMU second NIC, and failover.
