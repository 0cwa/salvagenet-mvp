# Roadmap tooling instructions

- GitHub Issues, milestones, and issue dependencies become authoritative only after bootstrap completes.
- `.github/roadmap/seed.v1.json` is reviewed bootstrap input, not a second steady-state roadmap.
- Generated snapshots are caches/publication inputs and must include schema version, generation time, source hash, and fallback state.
- Network failures may use one recent complete snapshot. Structural errors must fail.
- Never publish partial dependency data.
- Never fetch issue data from the visitor's browser.
- Keep the public snapshot and agent index compact; exclude full issue bodies, comments, review threads, logs, attachments, and credentials.
- The issue graph describes planned outcomes. `agents/task-dag.json` remains implementation authorization. Acceptance evidence remains claim authorization.
- Before a new phase, tooling must support agents in splitting, merging, reordering, deferring, or removing queued issues without silently weakening durable goals or acceptance coverage.
- Bootstrap and sync commands must be idempotent. After bootstrap, they may verify existing issue bodies and metadata but must not overwrite legitimate issue refinements without an explicit migration mode.
