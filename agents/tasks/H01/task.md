# H01 — Authenticated resumable artifact upload

## Status

**IN PROGRESS — implementation exists, hardening and CI remain.**

The branch `agent/H01-artifact-upload` contains the first end-to-end implementation in commit `1567b6694dd642a6606f62ec70965be4019cd88c`. It is not merge-ready until the recovery, cleanup, HTTP-semantics, and concurrency items below are resolved and the full repository workflow is green.

## Outcome

Add a controller-authenticated, resumable, digest-verified upload resource so a local or tailnet controller can deliver VM images without weakening the hardened URL downloader.

## Prerequisites

None; the branch is based on current `main`, including the merged HIL evidence hardening from H04.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Implemented on this branch

- Typed create, status, sequential chunk, complete, and cancel resources.
- A 1 MiB maximum chunk size with per-chunk SHA-256 verification.
- Exact replay idempotency for already committed chunks.
- App-private staged payload and metadata with restart-visible committed progress.
- Whole-file size and SHA-256 verification before publication.
- Publication into the existing digest-addressed payload and active-manifest layout.
- `image.resumable-upload` capability discovery.
- Controller CLI/client support that resumes from the host-reported committed offset.
- OpenAPI and Kotlin/Python regression coverage.
- The existing HTTPS importer and its SSRF/DNS-rebinding policy remain separate and unchanged.

## Remaining merge blockers

1. Recover the crash window where the payload moved into its digest-addressed destination but the active manifest was not yet published.
2. Garbage-collect cancelled and stale upload directories so they cannot exhaust the bounded upload count.
3. Return `404 Not Found` for an absent upload resource.
4. Validate the persisted upload metadata version and exact field set before recovery.
5. Validate the exact active-manifest field set when detecting an already published artifact.
6. Avoid hashing an already published large artifact during upload creation when trusted manifest and size metadata already prove the requested digest.
7. Map upload state, offset, replay, and idempotency conflicts to `409 Conflict` rather than generic `400 Bad Request`.
8. Serialize or explicitly arbitrate publication shared by resumable upload and HTTPS import so the active manifest does not have undocumented last-completion-wins behavior.

## Acceptance

- OpenAPI describes create/status/chunk/complete/cancel resources with bounded sizes, authentication, idempotency, `404`, and `409` behavior.
- Upload progress and publication intent survive process/repository recreation, including the payload-moved/manifest-not-yet-written crash window.
- Exact replay succeeds; gaps, partial overlaps, conflicting replay, oversized chunks, and digest mismatches are rejected deterministically.
- Completion fsyncs staged bytes and atomically publishes exactly one internally consistent active manifest; partial files are never active.
- Cancellation and stale-upload collection are bounded, reclaim staging state, and never delete an active artifact.
- Concurrent upload/import publication follows an explicit deterministic policy.
- The public HTTPS downloader retains its origin, redirect, DNS-rebinding, size, digest, cancellation, and atomic-publication protections.

## Required checks

```sh
make validate
make test-jvm
make test-android
python3 -m unittest discover -s controller/mvp-cli/tests
python3 tools/agents/verify-scope.py H01
```

GitHub CI must also complete the packaged APK, signature, and 16 KiB alignment jobs before merge.

## Handoff

Report commit SHA(s), exact tests and lab runs, evidence paths, checks unavailable in the current environment, concrete deferred items, and the smallest next blocker. Do not describe H01 as complete while any item under **Remaining merge blockers** is open.
