# H01 — Authenticated resumable artifact upload

## Outcome

Add a controller-authenticated, resumable, digest-verified upload resource so a local or tailnet controller can deliver VM images without weakening the hardened URL downloader.

## Prerequisites

None; active-cycle base is current `main`.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Acceptance

- OpenAPI describes create/status/chunk/complete/cancel resources with bounded sizes and idempotency.
- Upload progress and publication intent survive process/repository recreation.
- Overlapping, out-of-order, oversized, and digest-mismatched chunks are rejected deterministically.
- Completion fsyncs and atomically publishes one artifact manifest; partial files are never active.
- Cancellation and stale-upload collection are bounded and do not delete active artifacts.
- The public-HTTPS downloader retains its SSRF and DNS-rebinding protections.

## Required checks

```sh
make validate
make test-jvm
make test-android
python3 -m unittest discover -s controller/mvp-cli/tests
```

## Handoff

Report commit SHA(s), exact tests and lab runs, evidence paths, checks unavailable in the current environment, concrete TODOs, and the smallest next blocker.
