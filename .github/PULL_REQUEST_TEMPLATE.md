## Task

- Active task packet or reason for unpacketized maintenance:
- Acceptance criteria completed:
- Evidence class: static/unit | host-QEMU | emulator | physical Android | research

## Scope

- Modules changed:
- Intentional cross-module changes:
- Public contract or migration changes:

## Verification

- [ ] `make validate`
- [ ] `make dev-check` or the packet's stricter checks
- [ ] Relevant JVM/Android/guest/lab tests
- [ ] `python3 tools/agents/verify-scope.py <TASK>` when packeted
- [ ] Physical evidence attached only when actually required and executed
- [ ] No emulator/host-QEMU result is represented as a physical gate pass

## Deferred work

List only concrete `TODO(MVP-HARDENING, <task-id>)` items introduced by this change, with an expiry trigger.

## Provenance

Agent trailers are present on every agent-authored commit. Generated artifacts identify the exact source commit.
