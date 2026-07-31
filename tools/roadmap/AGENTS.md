# Roadmap tooling instructions

- GitHub Issues, milestones, and issue dependencies own planning state only after reviewed bootstrap.
- `GOAL.md` and accepted ADRs own durable direction; the active DAG owns implementation authorization; acceptance evidence owns product claims.
- The bootstrap seed is one-time reviewed input. Never overwrite edited live issue bodies, state, dependencies, or planning notes after bootstrap.
- Network failure may use a recent complete snapshot. Structural errors, partial dependency data, duplicate stable IDs, cycles, invalid paths, or missing acceptance coverage must fail.
- Keep snapshots schema-versioned, deterministic, bounded, and free of full issue bodies, comments, logs, attachments, credentials, and raw API payloads.
- Keep work state, dependency state, task authorization, pull-request state, and acceptance status separate. Report disagreement instead of silently reconciling it.
- Per-issue context is bounded and excludes comments by default.
- GitHub writes require an explicit dry-run/apply boundary, stable IDs, minimal permissions, and rate-limit backoff.
