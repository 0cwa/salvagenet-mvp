# F01 — Canonical artifact and profile resolution

Status: **MERGE READY** on `agent/F01-canonical-artifact-profile-resolution`.

Generate scoped context with:

```sh
make context TASK=F01
```

Reviewed implementation head `b0dae0581c9d72ae0f7481f7b602573931fbc3a2` passed the complete workflow in Actions run `30548116488`. The downloaded APK matched the commit-bound evidence files exactly. All actionable PR #7 findings were addressed: module-relative Gradle tooling paths, traversal-safe guest-init paths, robust manifest listing, pre-mutation validation, one verified artifact resolution per preparation, 1 MiB streaming copies, and expanded regression coverage.

The final documentation head must pass the same workflow before merge. After F01 merges, activate only the narrowed guest-boot qualification task; guest mesh and both emulator tasks remain queued for their own phase-start reviews.
