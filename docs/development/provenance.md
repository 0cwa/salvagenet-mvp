# Agent provenance

## Commit trailers

Each agent-authored commit records:

```text
Agent-Model: exact runtime-reported model identifier
Agent-Run-ID: stable identifier for the invocation/session
Agent-Task-ID: Txx
Agent-Mode: goal|interactive|human-review
Agent-Reasoning: explicit caller-supplied declaration
```

The commit helper requires the corresponding `AGENT_MODEL`, `AGENT_RUN_ID`,
`AGENT_TASK_ID`, `AGENT_MODE`, and `AGENT_REASONING` environment variables. It
does not infer missing values; use the explicit value `unknown` or
`not-applicable` when appropriate. `Agent-Reasoning` is a bounded metadata
declaration, never a prompt, transcript, or chain-of-thought archive.

Trailers are queryable through Git and do not require a noisy mutable ledger:

```sh
tools/provenance/report.sh <base-sha> <head-sha>
```

The report requires an explicit range. It is intentionally not a repository-wide
history scan; older commits remain readable without being rewritten.

## Why no prompt archive

Prompts, chain-of-thought, and large transcripts create privacy, context, and merge problems. The durable record is:

- task packet;
- code and tests;
- commit trailers;
- concise commit/PR explanation;
- experiment result when evidence changes architecture.

## Human changes

Use `Agent-Model: human` and a meaningful run ID when a human performs the implementation commit, and supply the remaining fields explicitly. Merge commits may omit trailers; their parents retain provenance.
