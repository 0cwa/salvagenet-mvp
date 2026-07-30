# node-shell production-package instructions

This package is the Android lifecycle and composition edge. It is not a general home for new domain or adapter policy.

- `NodeHostGraph` constructs adapters; it must not become a second domain model.
- New files should own one concern: composition, lifecycle, enrollment, control, artifact transfer, profile/artifact resolution, or runtime.
- Host API handlers call use cases/ports. They do not implement artifact transfer, download policy, SQL schema creation, QEMU command logic, or Tailscale state machines inline.
- All product tables and migrations belong to `node-store`; runtime `CREATE TABLE` statements in request paths are prohibited.
- Public artifact import and controller upload remain separate adapters but share one publication namespace only through explicit serialization or conflict arbitration.
- Publication, image listing, and runtime consumption must use one strict versioned artifact-manifest contract. Do not add another ad hoc `JSONObject` interpretation in a consumer.
- Resumable upload staging is app-private, versioned, exact-field validated, bounded in count/bytes/age, and recoverable after every durable step.
- Chunk data and metadata are fsynced before committed progress is exposed. Exact replay is idempotent; gaps, partial overlaps, and conflicting replay fail without mutating staging state.
- Publication moves data into a digest-addressed immutable payload and then atomically replaces an exact active manifest. Recovery must handle the payload-moved/manifest-not-written crash window.
- Cancellation and stale collection reclaim staging state but never delete a payload referenced by an active valid manifest.
- The HTTPS importer must preserve origin, redirect, DNS-rebinding, size, digest, cancellation, and atomic-publication invariants.
- Production profile resolution consumes packaged validated JSON and the packaged registry index; a complete Kotlin mirror is prohibited.
- `AndroidQemuProfileStorage` resolves only current canonical contracts and explicitly named current packaging adapters. It must not perform historical migrations or dual-format reads in its steady-state path.
- If a real released population later requires migration, put it in a separate `*Migration.kt` or compatibility package, execute it at an explicit lifecycle boundary, and keep the canonical resolver unaware of the obsolete format.
- Compatibility code requires an authorized task, identified deployed state, tests, a bounded support window, and a deletion trigger. Unused development builds and test fixtures do not qualify.
- Name the current Podroid bare-artifact seam as a packaging adapter, not generic legacy support; it must remain restricted to the exact pinned Podroid artifacts.
- Activity/task removal is never a runtime stop command. Stock mode reconciles after first unlock.
- Further broad extraction waits for a demonstrated review/debugging blocker or physical result.
