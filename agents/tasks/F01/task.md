# F01 — Canonical artifact and profile resolution

## Status

**MERGED.** PR #7 landed at `246d551ca7e691a0319a4b30e29d6e4905cd9910`. Exact final head `31dcd75199928b7887132a1429392266388c0b60` passed Actions run `30549498423`, including static/contracts, JVM/domain, Android tests and lint, guest/profile qualification, APK construction, exact canonical asset verification, Podroid runtime verification, signature, 16 KiB alignment, and candidate upload.

## Outcome

Make the checked-in VM profile JSON and the project artifact-manifest contract the exact production inputs used by the Android runtime, so later host-QEMU, emulator, and physical tests exercise the same configuration semantics.

## Why this was foundational

The repository said profile JSON was canonical, but `AndroidQemuProfileStorage` constructed the three production profiles in Kotlin and independently parsed artifact manifests. The drift was concrete: Ubuntu JSON required `virtio-block`, `virtio-net`, and `serial-console`, while the Kotlin mirror omitted those qualification checks. A lab could therefore pass against checked-in profile data while the APK executed a different model.

## Prerequisites

- H01 merged at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`.
- H04 merged at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`.
- Phase 0 realignment merged at `9e497bd33ad8c8a05e2cda9d0ba2e9ffd7a673f7` after Actions run `30524765854` passed.
- Profile schemas and examples passed repository validation.

## Phase-start review

- Profile loading and manifest unification remained one cohesive task because both were concentrated in the Android storage/resource boundary.
- The Android runtime uses a strict packaged-profile parser; build-time JSON Schema validation remains authoritative and runtime parsing repeats security/correctness constraints without adding a JSON Schema runtime dependency.
- The generated profile package contains the exact three JSON files, schema, index, and required guest-init assets under a stable namespaced root.
- Manifest producers and consumers are inventoried in `docs/research/experiments/F01.md`.
- Steady-state bare-file resolution is limited to `podroid-kernel`, `podroid-initramfs`, and `podroid-alpine-squashfs`. Every non-Podroid artifact requires a valid active manifest.
- H02, H03, qcow2 semantic changes, native source builds, UI rewrites, controller replacement, process isolation, and USB remained out of scope.

## Allowed paths

See `allowed-paths.txt`. This packet is retained as historical provenance; it no longer authorizes edits. The sole active packet is `agents/tasks/H02A/task.md`.

## Acceptance criteria

- [x] Packaged, build-validated JSON is the sole production source for `alpine-direct-qualification`, `ubuntu-2404-arm64-uefi`, and `k3s-worker-lab`.
- [x] Android production code no longer duplicates complete profile definitions in a Kotlin `when` or equivalent mirror.
- [x] Profile loading is bounded, rejects unknown fields, unsupported contracts, and traversal segments, validates fixed Android/QEMU compatibility fields, preserves typed domain values, and fails closed before QEMU or mutable disk effects.
- [x] The APK/package test proves the exact profile JSON, schema, index, and required guest-init assets are present.
- [x] Artifact publication, image listing, cleanup, installed checks, and runtime consumption of active manifests use one strict versioned contract with exact fields, digest, size, immutable relative path, and root-containment checks.
- [x] Legacy bare fallback is restricted to the three pinned Podroid qualification artifacts; all non-Podroid artifacts require active manifests.
- [x] Artifact preparation reuses one verified source resolution per preparation and uses a 1 MiB streaming copy buffer with copied-byte digest verification.
- [x] Manifest listing ignores invalid stray filenames and a remove-after-list race, but continues to fail closed for malformed valid manifests and the explicit active-manifest count invariant.
- [x] H01 upload behavior and the hardened public HTTPS importer retain their authentication, SSRF, idempotency, digest, size, recovery, cancellation, and atomic-publication invariants.
- [x] All actionable PR #7 review findings are addressed with regression coverage.
- [x] Typed QEMU, profile, guest, Android, package, signature, and alignment checks are green.
- [x] No result is represented as physical Android evidence, and no base-MVP gate changes status.

## Required checks

The exact final head passed:

```sh
make validate
make test-jvm
make test-android
make test-guest
python3 tools/agents/verify-scope.py F01
```

GitHub Actions run `30549498423` also passed APK packaging, canonical profile-asset verification, Podroid runtime verification, signature verification, 16 KiB alignment, and candidate-artifact upload.

```text
mergeCommit: 246d551ca7e691a0319a4b30e29d6e4905cd9910
validatedHead: 31dcd75199928b7887132a1429392266388c0b60
workflowRun: 30549498423
workflowArtifactId: 8762334271
workflowArtifactDigest: sha256:6163f03ca995a366f6e2d47a53e9d70c33adce23eaf0dd80e76ea212351da868
apkSha256: f423bd939f97be119250318ca1c871df0ff9bc25a67b0e5672cc75c6d668e7f9
apkSizeBytes: 348568385
signatureVerified: true
alignment16KiBVerified: true
hardwareValidated: false
```

## Phase-end verification

- [x] Every acceptance criterion was checked against code, tests, review feedback, and downloaded package evidence.
- [x] Production Kotlin contains no complete profile mirror and no direct active-manifest parser outside `ArtifactManifestStore`.
- [x] An isolated non-Podroid bare file cannot satisfy Ubuntu/AAVMF resolution.
- [x] The unused pre-release Ubuntu/AAVMF migration was removed because no deployed state requires it.
- [x] All valid PR #7 findings were addressed and the exact final head passed the complete applicable workflow.
- [x] H02/H03 were re-evaluated: H02 was split; only H02A is active, while H02B and H03 remain queued.

## Handoff

F01 is complete and historical. Do not reopen its scope during H02A unless new evidence proves a direct correctness blocker in the canonical profile or manifest boundary. H02A must qualify the guest boot path without guest mesh behavior and without claiming Android evidence.
