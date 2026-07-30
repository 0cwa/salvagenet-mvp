# H01 — artifact upload

Status: **implementation under hardening** on `agent/H01-artifact-upload`.

Generate the current scoped context with:

```sh
make context TASK=H01
```

Read `task.md` and `docs/research/experiments/H01.md` before editing. The first implementation exists; the next work is the bounded recovery/cleanup/HTTP-semantics list in `task.md`, not a redesign of the upload protocol.

H01 is complete only after the task-local checks, scope verifier, and full GitHub Android/package workflow are green.
