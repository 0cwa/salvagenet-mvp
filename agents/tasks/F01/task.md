# F01 — Canonical artifact and profile resolution

## Status

**MERGE READY.** Implementation head `71a04acedd11221fbefe2c0fa43984141ec11ed4` passed Actions run `30543765626`, including static/contracts, JVM/domain, Android tests and lint, guest/profile qualification, APK construction, exact canonical asset verification, Podroid runtime verification, signature, 16 KiB alignment, and candidate upload.

## Outcome

Make the checked-in VM profile JSON and the project artifact-manifest contract the exact production inputs used by the Android runtime, so later host-QEMU, emulator, and physical tests exercise the same configuration semantics.

## Why this is foundational

The repository said profile JSON was canonical, but `AndroidQemuProfileStorage` constructed the three production profiles in Kotlin and independently parsed artifact manifests. The drift was concrete: Ubuntu JSON required `virtio-block`, `virtio-net`, and `serial-console`, while the Kotlin mirror omitted those qualification checks. A lab could therefore pass against checked-in profile data while the APK executed a different model.

## Prerequisites

- H01 merged at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`.
- H04 merged at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`.
- Phase 0 realignment merged at `9e497bd33ad8c8a05e2cda9d0ba2e9ffd7a673f7` after Actions run `30524765854` passed.
- Current profile schemas and examples passed repository validation.

## Phase-start review

- Profile loading and manifest unification remained one cohesive task because both were concentrated in the Android storage/resource boundary.
- The Android runtime uses a strict packaged-profile parser; build-time JSON Schema validation remains authoritative and runtime parsing repeats security/correctness constraints without adding a JSON Schema runtime dependency.
- The generated profile package contains the exact three JSON files, schema, index, and required rendered guest-init assets under a stable namespaced root.
- Manifest producers and consumers are inventoried in `docs/research/experiments/F01.md`.
- Steady-state bare-file resolution is limited to `podroid-kernel`, `podroid-initramfs`, and `podroid-alpine-squashfs`. A complete digest-verified pre-F01 Ubuntu/AAVMF bare bundle may migrate once into strict active manifests; an isolated bare non-Podroid artifact remains rejected.
- H02, H03, qcow2 semantic changes, native source builds, UI rewrites, controller replacement, process isolation, and USB remain out of scope.

## Allowed paths

See `allowed-paths.txt`. Phase status and roadmap updates are included only to record this task's verified result; implementation scope remains inside the selected profile/artifact boundary.

## Acceptance criteria

- [x] Packaged, build-validated JSON is the sole production source for `alpine-direct-qualification`, `ubuntu-2404-arm64-uefi`, and `k3s-worker-lab`.
- [x] Android production code no longer duplicates complete profile definitions in a Kotlin `when` or equivalent mirror.
- [x] Profile loading is bounded, rejects unknown fields and unsupported contracts, validates fixed Android/QEMU compatibility fields, preserves typed domain values, and fails closed before QEMU or mutable disk effects.
- [x] The APK/package test proves the exact profile JSON, schema, index, and rendered guest-init assets required by those profiles are present.
- [x] Artifact publication, image listing, cleanup, installed checks, and runtime consumption of active manifests use one strict versioned contract with exact fields, digest, size, immutable relative path, and root-containment checks.
- [x] Steady-state legacy fallback is restricted to the three pinned Podroid qualification artifacts; a complete verified historical Ubuntu/AAVMF bundle is upgraded into active manifests, while an isolated bare non-Podroid artifact fails closed.
- [x] H01 upload behavior and the hardened public HTTPS importer retain their authentication, SSRF, idempotency, digest, size, recovery, cancellation, and atomic-publication invariants.
- [x] Typed QEMU, profile, guest, Android, package, signature, and alignment checks are green.
- [x] No result is represented as physical Android evidence, and no base-MVP gate changes status.

## Required checks

The validated implementation head passed:

```sh
make validate
make test-jvm
make test-android
make test-guest
python3 tools/agents/verify-scope.py F01
```

GitHub Actions run `30543765626` also passed APK packaging, canonical profile-asset verification, Podroid runtime verification, signature verification, 16 KiB alignment, and candidate-artifact upload.

```text
validatedHead: 71a04acedd11221fbefe2c0fa43984141ec11ed4
workflowRun: 30543765626
workflowArtifactId: 8760011060
workflowArtifactDigest: sha256:6f2e873938f7e5dcf536862ec310e151d240bde4b1c363b377e972133aaf82c4
apkSha256: 9724c1ae58299f961c850749f3b14aa1b10a9cbc7f988d9b8b9243352da76da0
apkSizeBytes: 348566113
signatureVerified: true
alignment16KiBVerified: true
hardwareValidated: false
```

## Phase-end verification

- [x] Every acceptance criterion was checked against code, tests, and downloaded package evidence.
- [x] Production Kotlin contains no complete profile mirror and no direct active-manifest parser outside `ArtifactManifestStore`.
- [x] An isolated non-Podroid bare file cannot satisfy Ubuntu/AAVMF resolution.
- [x] A complete digest-verified pre-F01 Ubuntu/AAVMF bundle migrates to active manifests before use.
- [x] The required checks and complete applicable CI workflow passed.
- [x] H02/H03 were re-evaluated: activate only guest boot qualification after merge; guest mesh and both emulator tasks remain queued.

## Handoff

Merge only the exact final documentation head after it passes the complete workflow. After merge, record the merge SHA, archive F01 as merged, and activate one narrowly scoped guest-boot qualification task. Keep guest mesh and both emulator tasks queued until their stated prerequisites pass. No physical gate changes status.
