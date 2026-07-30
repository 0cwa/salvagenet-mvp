# H01 — artifact upload

Status: **MERGE READY** on `agent/H01-artifact-upload`.

Generate the final scoped context with:

```sh
make context TASK=H01
```

The selected protocol and all previously recorded merge blockers are resolved. `task.md` is the authoritative implementation and validation summary; `docs/research/experiments/H01.md` records the design findings and resolution.

GitHub Actions run `30509824017` passed the complete static, JVM, Android, lint, guest, packaging, signature, 16 KiB alignment, and candidate-artifact workflow. No physical acceptance gate is changed by H01.

After PR #5 merges, update the active cycle status from `MERGE_READY` to `MERGED` with the merge commit rather than extending this task silently.
