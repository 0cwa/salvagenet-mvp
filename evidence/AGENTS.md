# Acceptance evidence instructions

- Commit only compact, redacted JSON summaries and small deterministic fixtures.
- Never commit auth keys, controller capabilities, private keys, full logcat,
  guest data, model transcripts, or large binary output.
- One file per acceptance gate: `gates/Bxx.json` or `gates/Uxx.json`.
- `PASS` requires a reproducible command and artifact/log reference; unrun
  physical checks are `BLOCKED-HARDWARE`, not inferred.
- Git commit trailers carry agent provenance; do not duplicate prompt history.
