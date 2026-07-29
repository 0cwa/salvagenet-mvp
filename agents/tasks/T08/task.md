# T08 — QA, failure injection, and evidence

## Outcome

Run automated and authorized hardware tests, fix bounded failures, and update the acceptance ledger with evidence.

## Prerequisites

T07

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- Automated base gates pass.
- Physical gates are PASS or explicitly BLOCKED-HARDWARE.
- Secrets/redaction/release-surface checks pass.
- Fixed failures gain regression tests.
- MVP+ gate matches the ledger.

## Required checks

```sh
make validate
make test-jvm
make test-android
tests/e2e/run.sh
python3 tools/ci/check-mvp-plus-gate.py --report-only
```

## Handoff

Report commit SHA(s), tests run, hardware checks not run, changed contracts, specific TODOs, and the smallest next blocker.
