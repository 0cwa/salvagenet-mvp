# F01 — Canonical artifact and profile resolution

Status: **MERGE READY** on `agent/F01-canonical-artifact-profile-resolution`.

Generate scoped context with:

```sh
make context TASK=F01
```

The complete phase-start review, implementation findings, exact CI run, candidate APK identity, acceptance checklist, and next-phase decision are recorded in `docs/research/experiments/F01.md`.

F01 must merge as the exact final tested documentation head before the next phase is activated. The original broad H02/H03 packets remain queued; the phase-end decision is to replace them with narrower guest-boot, guest-mesh, emulator-harness, and emulator-scenario tasks, activating only guest boot first.