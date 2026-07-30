# H04 — HIL evidence hardening

## Outcome

Harden the already-merged `tests/hil/` runner so scarce borrowed or streamed device sessions produce exact, reviewable gate evidence without adding a second physical-test implementation.

## Prerequisites

None; `tests/hil/` is present on the active-cycle base.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- SSH known-host state is isolated per run or explicitly tied to the configured device/guest identity.
- Headscale node assertions use exact structured identity matching rather than broad substring matches.
- Controller-silent smoke and actual controller/network-unavailable evidence are represented as distinct assertions; only the latter may support B17.
- The runner has an explicit remote-device-streaming adapter seam while preserving exact serial selection and exit 77 behavior.
- Interrupted runs retain bounded redacted diagnostics but cannot emit a PASS record.
- Reviewed run output can be validated and promoted through the existing evidence schema/tooling without manual JSON edits.

## Required checks

```sh
make validate
PYTHONPATH=. python3 -m unittest discover -s tests/hil -p 'test_*.py' -v
tests/hil/run.py --help
```

## Handoff

Report commit SHA(s), exact tests, checks unavailable without a device, evidence paths, concrete deferred items, and the smallest next blocker.
