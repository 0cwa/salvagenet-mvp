# Agent provenance

## Commit trailers

Each agent-authored commit records:

```text
Agent-Model: exact runtime-reported model identifier
Agent-Run-ID: stable identifier for the invocation/session
Agent-Task-ID: Txx
Agent-Mode: goal|interactive|human-review
```

Trailers are queryable through Git and do not require a noisy mutable ledger:

```sh
make provenance-report
```

## Why no prompt archive

Prompts, chain-of-thought, and large transcripts create privacy, context, and merge problems. The durable record is:

- task packet;
- code and tests;
- commit trailers;
- concise commit/PR explanation;
- experiment result when evidence changes architecture.

## Human changes

Use `Agent-Model: human` and a meaningful run ID when a human performs the implementation commit. Merge commits may omit trailers; their parents retain provenance.
