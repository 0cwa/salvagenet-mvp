# F01 — Canonical artifact and profile resolution

Status: **MERGE READY** on `agent/F01-canonical-artifact-profile-resolution`.

Generate scoped context with:

```sh
make context TASK=F01
```

Implementation head `71a04acedd11221fbefe2c0fa43984141ec11ed4` passed the complete workflow in Actions run `30543765626`. The checked-in profile JSON and rendered guest-init assets are the packaged production source, active artifacts use one strict manifest contract, isolated non-Podroid bare artifacts fail closed, and a complete digest-verified pre-F01 Ubuntu/AAVMF bundle migrates once into the manifest layout.

The final documentation head must pass the same workflow before merge. After F01 merges, activate only the narrowed guest-boot qualification task; guest mesh and both emulator tasks remain queued for their own phase-start reviews.
