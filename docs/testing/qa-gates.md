# Base-MVP QA gates

## Automated before device work

- repository and AGENTS/task validation;
- schemas and all example documents valid;
- domain/application dependency rules pass;
- profile registry accepts Alpine, Ubuntu, and K3s-lab profiles;
- QEMU baseline and profile argv snapshots pass;
- no release source exposes raw QEMU/kernel override entry points;
- operation state transition and idempotency tests pass;
- Room schema exported and migration baseline checked;
- Host API examples conform to OpenAPI;
- secrets scanner finds no live material;
- MVP+ gate prevents USB implementation scheduling.

## Physical-device base gates

- imported Podroid baseline boots before refactoring;
- fork launches APK-packaged QEMU after refactoring;
- exactly one QEMU process;
- Activity removal does not change desired VM state;
- service/process death results in deterministic reconciliation;
- first-unlock reboot recovery works;
- host embedded Tailscale joins local Headscale;
- controller reaches Host API through host mesh;
- Ubuntu profile boots and becomes SSH reachable;
- guest joins Headscale with a separate identity;
- recovery SSH path works with guest mesh disabled;
- stop is graceful before force escalation;
- reset-system preserves the data disk;
- no default password or non-loopback recovery listener;
- diagnostics redact imported secrets.

## K3s qualification gate

The `k3s-worker-lab` profile emits a machine-readable report. It may be `qualified`, `qualified-with-warnings`, or `unsupported`; cluster join is not required.

## MVP+ gate

Every base item in `docs/roadmap/acceptance-ledger.md` must be `PASS` before T09 can change executable USB-link code.
