# F02 — Device-lab readiness

Status: **IN PROGRESS** on `agent/F02-device-lab-readiness`.

Generate scoped context with:

```sh
make context TASK=F02
```

This phase hardens the existing single-phone runner and repository truth before agent-automated local device testing. It does not change QEMU, guest profiles, enrollment semantics, or acceptance-gate status.
