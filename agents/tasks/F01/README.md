# F01 — Canonical artifact and profile resolution

Status: **IN PROGRESS — post-exit hardening** on `agent/F01-canonical-artifact-profile-resolution`.

Generate scoped context with:

```sh
make context TASK=F01
```

The initial implementation head passed the full workflow, but focused phase-end review found that bare-file legacy artifact fallback was not restricted to the three pinned Podroid qualification artifacts. The branch now requires active manifests for Ubuntu and AAVMF inputs and includes a regression test. This updated head must pass the full workflow before F01 returns to merge-ready.

The original broad H02/H03 packets remain queued. The phase-end direction remains to split them into guest boot, guest mesh, emulator harness, and emulator scenarios, activating only guest boot first after F01 merges.