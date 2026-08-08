# Agent provenance

Git commit trailers are the durable, merge-friendly source of implementation
authorship metadata:

```text
Agent-Model: <exact runtime-reported identifier>
Agent-Run-ID: <runner-provided stable identifier>
Agent-Task-ID: T02
Agent-Mode: <explicit caller-supplied mode>
Agent-Reasoning: <explicit caller-supplied declaration>
```

Use `tools/provenance/commit-agent.sh` with all five metadata environment
variables set. Never guess or normalize a value; callers may explicitly use
`unknown` or `not-applicable` when a value is unavailable or does not apply.
The helper accepts ordinary environment variables and invokes Git directly, so
it is usable from any harness that can provide those inputs. `Agent-Reasoning`
is metadata only: do not put prompts, transcripts, or chain-of-thought in it.
The repository intentionally avoids a shared mutable per-run ledger: parallel
agents would conflict on it and it would grow into irrelevant context.
`tools/provenance/report.sh` derives the deterministic report from Git history.
Pass an explicit `BASE SHA HEAD SHA` pair or `BASE..HEAD` range; it never scans
all history by default.

`scaffold-generation.json` records this initial artifact generation only. It is
not updated by implementation agents.
