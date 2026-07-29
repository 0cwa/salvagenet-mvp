# Documentation instructions

Read `docs/INDEX.md`, then only the page named by your task packet.

- Architecture pages record durable constraints and explicit flexibility points.
- ADRs record decisions; do not silently reverse them in implementation code.
- Research pages contain evidence and open questions, not implementation authority.
- Roadmap pages are the integration plan; task packets remain the unit of agent work.
- Keep each page under roughly 250 lines. Split detail instead of creating an all-purpose design document.
- When changing a durable decision, update its ADR and the relevant acceptance criterion in the same change.
- `docs/roadmap/acceptance-ledger.md` and `evidence/gates/*.json` are the status authority.
- `docs/STATUS.md` and the README acceptance block are generated with `make mvp-status`; do not hand-edit them.
- Historical scaffold and overnight documents must not be presented as current product status.
- Release wording follows the ledger: use “device-lab candidate” until every base gate passes and exact artifact evidence is sealed.
