# Agent provenance

Git commit trailers are the durable, merge-friendly source of implementation
authorship metadata:

```text
Agent-Model: <exact runtime-reported identifier>
Agent-Run-ID: <runner-provided stable identifier>
Agent-Task-ID: T02
Agent-Mode: goal
```

Use `tools/provenance/commit-agent.sh`. Never guess or normalize a model name.
The repository intentionally avoids a shared mutable per-run ledger: parallel
agents would conflict on it and it would grow into irrelevant context.
`tools/provenance/report.sh` derives the deterministic report from Git history.

`scaffold-generation.json` records this initial artifact generation only. It is
not updated by implementation agents.
