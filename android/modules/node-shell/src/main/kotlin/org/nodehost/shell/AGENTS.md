# node-shell production-package instructions

This package is the Android lifecycle and composition edge. It is not a general home for new domain or adapter policy.

- `NodeHostGraph` constructs adapters; it must not become a second domain model.
- New files should own one concern: `composition`, `lifecycle`, `enrollment`, `control`, or `runtime`.
- Host API handlers call use cases/ports. They do not implement artifact download policy, SQL schema creation, QEMU command logic, or Tailscale state machines inline.
- All product tables and migrations belong to `node-store`; runtime `CREATE TABLE` statements in request paths are prohibited.
- Artifact import/publication must sit behind an application port and preserve SSRF, digest, size, cancellation, and atomic-publication invariants.
- Activity/task removal is never a runtime stop command. Stock mode reconciles after first unlock.
- Do not perform a broad package split before D02/D03; extract only after a physical result proves the boundary and contract.
