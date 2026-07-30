# node-shell production-package instructions

This package is the Android lifecycle and composition edge. It is not a general home for new domain or adapter policy.

- `NodeHostGraph` constructs adapters; it must not become a second domain model.
- New files should own one concern: `composition`, `lifecycle`, `enrollment`, `control`, `artifact transfer`, or `runtime`.
- Host API handlers call use cases/ports. They do not implement artifact transfer, artifact download policy, SQL schema creation, QEMU command logic, or Tailscale state machines inline.
- All product tables and migrations belong to `node-store`; runtime `CREATE TABLE` statements in request paths are prohibited.
- Public artifact import and controller upload remain separate adapters but share one publication namespace only through explicit serialization or conflict arbitration.
- Resumable upload staging is app-private, versioned, exact-field validated, bounded in count/bytes/age, and recoverable after every durable step.
- Chunk data and metadata are fsynced before committed progress is exposed. Exact replay is idempotent; gaps, partial overlaps, and conflicting replay fail without mutating staging state.
- Publication moves data into a digest-addressed immutable payload and then atomically replaces an exact active manifest. Recovery must handle the payload-moved/manifest-not-written crash window.
- Cancellation and stale collection reclaim staging state but never delete a payload referenced by an active valid manifest.
- The HTTPS importer must preserve origin, redirect, DNS-rebinding, size, digest, cancellation, and atomic-publication invariants.
- Activity/task removal is never a runtime stop command. Stock mode reconciles after first unlock.
- Do not perform a broad package split before D02/D03; extract only after a physical result proves the boundary and contract.
