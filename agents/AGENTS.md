# Agent orchestration instructions

This tree contains task packets, not product implementation.

- The orchestrator owns dispatch, dependency order, integration, and acceptance status.
- Implementation agents read their packet, generated context pack, and applicable nested `AGENTS.md` only.
- `task-dag.json` is authoritative for prerequisites and path ownership.
- Do not edit another task packet during implementation.
- T09 is blocked unless every base-MVP acceptance item is `PASS`.
- Keep packets compact; canonical architecture remains under `docs/`.
