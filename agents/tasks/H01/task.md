# H01 — Authenticated resumable artifact upload

## Status

**MERGE READY — implementation and full CI are green.**

The branch `agent/H01-artifact-upload` implements and hardens the complete H01 contract. GitHub Actions run `30509824017` passed repository validation, controller tests, JVM/domain tests, Android adapter tests and lint, guest/profile qualification, packaged APK verification, signature verification, 16 KiB alignment, and candidate artifact upload.

This status means software-merge ready. It does not constitute physical Android validation and changes no base-MVP acceptance gate.

## Outcome

Add a controller-authenticated, resumable, digest-verified upload resource so a local or tailnet controller can deliver VM images without weakening the hardened URL downloader.

## Prerequisites

None; the branch is based on current `main`, including the merged HIL evidence hardening from H04.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff.

## Implemented and validated

- Typed create, status, sequential chunk, complete, and cancel resources.
- A 1 MiB maximum chunk size with per-chunk SHA-256 verification.
- Exact replay idempotency for already committed chunks.
- App-private, versioned staged payload and metadata with restart-visible committed progress.
- Whole-file size and SHA-256 verification before publication.
- Recovery of the payload-moved/manifest-not-yet-published crash window, including when the upload is old enough for stale collection.
- Exact persisted metadata and active-manifest field/version validation.
- Bounded cancellation and stale-record collection without consuming open-upload capacity or deleting active artifacts.
- `404 Not Found` for missing uploads and `409 Conflict` for state, offset, replay, capacity, and idempotency conflicts.
- Publication into the existing digest-addressed payload and active-manifest layout.
- Process-local serialization shared by resumable upload and HTTPS import; serialized completion order determines the active manifest.
- Existing published artifacts are recognized through exact immutable digest-path, manifest, and size checks without rehashing the large payload during upload creation.
- `image.resumable-upload` capability discovery.
- Controller CLI/client support that hashes locally, streams bounded chunks, resumes only from host-reported committed progress, verifies every response, rejects local-file mutation, and redacts reflected credentials/idempotency keys.
- OpenAPI and Kotlin/Python regression coverage.
- The existing HTTPS importer retains its enrolled-origin, redirect, DNS-rebinding, deadline, size, digest, cancellation, and atomic-publication protections.
- Pre-H01 Host API bounds, diagnostics validation, apply conflict mapping, and recovery-session admission were restored after review detected regressions in the first implementation.

## Resolved merge blockers

1. **Resolved:** durable moved-payload recovery completes the active manifest before stale collection.
2. **Resolved:** cancelled and stale staging is bounded and reclaimed; only open uploads count against open capacity.
3. **Resolved:** absent upload resources return `404`.
4. **Resolved:** persisted metadata requires the exact supported version and field set.
5. **Resolved:** active manifests require the exact supported field set and immutable digest path.
6. **Resolved:** creation does not rehash an already-published immutable payload.
7. **Resolved:** upload and idempotency conflicts map to `409`.
8. **Resolved:** HTTPS import and controller upload share explicit publication serialization.

## Acceptance

- OpenAPI describes create/status/chunk/complete/cancel resources with bounded sizes, authentication, idempotency, `404`, and `409` behavior.
- Upload progress and publication intent survive process/repository recreation, including the payload-moved/manifest-not-yet-written crash window.
- Exact replay succeeds; gaps, partial overlaps, conflicting replay, oversized chunks, and digest mismatches are rejected deterministically.
- Completion fsyncs staged bytes and atomically publishes exactly one internally consistent active manifest; partial files are never active.
- Cancellation and stale-upload collection are bounded, reclaim staging state, and never delete an active artifact.
- Concurrent upload/import publication follows a documented serialized completion policy.
- The public HTTPS downloader retains its origin, redirect, DNS-rebinding, size, digest, cancellation, and atomic-publication protections.

## Validation

GitHub Actions run `30509824017` passed:

```text
repository/static/contracts/evidence validation
controller Python tests
guest/profile qualification
JVM/domain tests
Android adapter unit tests
Android lint
debug APK and mesh release packaging
APK signature verification
16 KiB alignment verification
candidate artifact/evidence upload
```

Physical transport, Android storage pressure, process death during a real multi-gigabyte transfer, and remote controller/device networking remain physical/integration evidence rather than software-CI claims.

## Handoff

Merge PR #5 without rewriting the tested commits. After merge, update the cycle registry to `MERGED` with the merge commit, then begin H02 or H03 from current `main`.
