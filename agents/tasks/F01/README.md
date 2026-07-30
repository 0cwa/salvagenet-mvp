# F01 — Canonical artifact and profile resolution

Status: **IN PROGRESS — PR review fixes are under revalidation** on `agent/F01-canonical-artifact-profile-resolution`.

Generate scoped context with:

```sh
make context TASK=F01
```

Implementation head `71a04acedd11221fbefe2c0fa43984141ec11ed4` previously passed the complete workflow in Actions run `30543765626`. PR #7 review then identified valid path-resolution, traversal, manifest-listing, large-artifact hashing, and regression-coverage improvements. Those fixes are committed, but the previous merge-ready evidence is superseded until the exact review-fix head passes the full workflow.

The checked-in profile JSON and the required guest-init assets remain the packaged production source. After F01 merges, activate only the narrowed guest-boot qualification task; guest mesh and both emulator tasks remain queued for their own phase-start reviews.
