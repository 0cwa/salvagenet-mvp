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
history scan; older commits remain readable without being rewritten. The
two-argument form is exactly `base..head`, so the base commit itself is not
reported and the head is included. A one-argument `base..head` invocation has
the same selection semantics. Empty, option-like, or unresolved endpoints fail
before a partial report is emitted.

The version-1 JSON report emits full commit IDs, subjects, all values for each
required trailer, and deterministically sorted changed paths. It fails loudly
for missing or blank required values and is bounded to 256 commits, 2,000 paths
per commit, 4,096 bytes per textual field, and 8 MiB total. These limits keep a
pull-request artifact reviewable; they are not evidence that the declarations
are true. `Agent-Model` and `Agent-Reasoning` remain caller declarations, not
independent provider or runtime attestations. A merge commit is reported once;
its changed paths use Git's combined diff rather than a per-parent expansion.

## Why no prompt archive

Prompts, chain-of-thought, and large transcripts create privacy, context, and merge problems. The durable record is:

- task packet;
- code and tests;
- commit trailers;
- concise commit/PR explanation;
- experiment result when evidence changes architecture.

## Human changes

Use `Agent-Model: human` and a meaningful run ID when a human performs the implementation commit, and supply the remaining fields explicitly. Merge commits may omit trailers; their parents retain provenance.
