# Agent orchestration instructions

This tree contains task packets, not product implementation.

- The orchestrator owns dispatch, dependency order, integration, and acceptance status.
- `task-dag.json` describes the active cycle; completed T00–T09 packets remain historical provenance only.
- Implementation agents read their packet, generated context pack, and applicable nested `AGENTS.md` only.
- Do not edit another active task packet during implementation.
- Active hardware-independent tasks may not convert physical-device gates to `PASS`.
- USB/AOA remains blocked unless every base-MVP acceptance item is `PASS`.
- Keep packets compact; canonical architecture remains under `docs/`.
