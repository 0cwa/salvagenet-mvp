# H01 — Authenticated resumable artifact upload

## Status

**MERGED — complete at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`.**

The validated branch head was `839f3638a4ee31e601d7f0c093596acc799c5b57`. GitHub Actions run `30510377089` passed repository validation, controller tests, JVM/domain tests, Android adapter tests and lint, guest/profile qualification, packaged APK verification, signature verification, 16 KiB alignment, and candidate artifact upload.

This is software integration evidence, not physical Android validation, and it changed no base-MVP acceptance gate.

## Outcome

Add a controller-authenticated, resumable, digest-verified upload resource so a local or tailnet controller can deliver VM images without weakening the hardened URL downloader.

## Implemented and validated

- Typed create, status, sequential chunk, complete, and cancel resources.
- A 1 MiB maximum chunk size with per-chunk SHA-256 verification.
- Exact replay idempotency for already committed chunks.
- App-private, versioned staged payload and metadata with restart-visible committed progress.
- Whole-file size and SHA-256 verification before publication.
- Recovery of the payload-moved/manifest-not-yet-published crash window, including when the upload is old enough for stale collection.
- Exact persisted metadata and active-manifest field/version validation at the upload boundary.
- Bounded cancellation and stale-record collection without consuming open-upload capacity or deleting active artifacts.
- `404 Not Found` for missing uploads and `409 Conflict` for state, offset, replay, capacity, and idempotency conflicts.
- Publication into the digest-addressed payload and active-manifest layout.
- Process-local serialization shared by resumable upload and HTTPS import; serialized completion order determines the active manifest.
- `image.resumable-upload` capability discovery.
- Controller CLI/client support that hashes locally, streams bounded chunks, resumes only from host-reported committed progress, verifies every response, rejects local-file mutation, and redacts reflected credentials/idempotency keys.
- The existing HTTPS importer retains its enrolled-origin, redirect, DNS-rebinding, deadline, size, digest, cancellation, and atomic-publication protections.

## Acceptance result

All H01 acceptance criteria passed in the validated head and full workflow. Remaining real-device concerns—storage pressure, process death during a large transfer, and remote networking—are integration evidence, not unfinished H01 implementation.

## Handoff

H01 is historical. Do not extend it silently. Artifact/profile contract follow-up belongs to active foundational task F01, and physical transfer evidence belongs to a scoped device-validation task.
