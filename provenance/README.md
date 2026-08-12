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
all history by default. The two-argument form reports the commits selected by
exactly `BASE..HEAD`; an empty range is valid and reports no commits. Missing or
blank required trailers fail the report instead of becoming empty metadata.

The JSON report has schema version `1` and this shape:

```json
{
  "schemaVersion": 1,
  "range": "BASE..HEAD",
  "commits": [
    {
      "sha": "full-commit-sha",
      "subject": "commit subject",
      "Agent-Model": ["..."],
      "Agent-Reasoning": ["..."],
      "Agent-Run-ID": ["..."],
      "Agent-Task-ID": ["..."],
      "Agent-Mode": ["..."],
      "changedFiles": ["path"]
    }
  ]
}
```

Commits are emitted in deterministic topological order (oldest first), trailer
values remain arrays so repeated values are visible, and changed paths are
sorted by their Git byte representation. A merge is one commit record; its
changed paths use Git's combined diff and are not expanded once per parent. The
report is bounded to 256 commits,
2,000 paths per commit, 4,096 bytes per subject/trailer/path, and 8 MiB total.
The pull-request workflow only reads the checked-out range and uploads this
credential-free JSON artifact; it does not call a GitHub API or mutate a pull
request.

`scaffold-generation.json` records this initial artifact generation only. It is
not updated by implementation agents.
