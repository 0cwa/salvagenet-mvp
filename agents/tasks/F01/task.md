# F01 — Canonical artifact and profile resolution

## Status

**IN PROGRESS — phase-start review passed on `main` at `9e497bd33ad8c8a05e2cda9d0ba2e9ffd7a673f7`.**

## Outcome

Make the checked-in VM profile JSON and the project artifact-manifest contract the exact production inputs used by the Android runtime, so later host-QEMU, emulator, and physical tests exercise the same configuration semantics.

## Why this is foundational

The repository says profile JSON is canonical, but `AndroidQemuProfileStorage` constructs the three production profiles in Kotlin and independently parses artifact manifests. The drift is concrete: Ubuntu JSON requires `virtio-block`, `virtio-net`, and `serial-console`, while the Kotlin mirror omits those qualification checks. A lab can therefore pass against checked-in profile data while the APK executes a different model.

## Prerequisites

- H01 merged at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`.
- H04 merged at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`.
- Phase 0 realignment merged at `9e497bd33ad8c8a05e2cda9d0ba2e9ffd7a673f7` after Actions run `30524765854` passed.
- Current profile schemas and examples pass repository validation.

## Phase-start review result

- Profile loading and manifest unification remain one cohesive task because both are concentrated in the Android storage/resource boundary.
- The Android runtime must use a strict packaged-profile parser; build-time JSON Schema validation remains authoritative and runtime parsing repeats the security/correctness constraints without adding a JSON Schema runtime dependency.
- The profile package must contain the exact three JSON files and their checked-in guest-init sources under a stable namespaced asset root.
- Manifest producers/consumers are inventoried in `docs/research/experiments/F01.md`.
- Built-in Podroid assets may retain their existing bare-file plus `.sha256` storage form, but that legacy form must be isolated behind the selected artifact repository. Every versioned active manifest is parsed and written by one strict contract adapter.
- H02, H03, qcow2 semantic changes, native source builds, UI rewrites, controller replacement, process isolation, and USB remain out of scope.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff and a phase-plan review.

## Acceptance criteria

- Packaged, build-validated JSON is the sole production source for `alpine-direct-qualification`, `ubuntu-2404-arm64-uefi`, and `k3s-worker-lab`.
- Android production code no longer duplicates complete profile definitions in a Kotlin `when` or equivalent mirror.
- Profile loading is bounded, rejects unknown fields/unsupported versions, validates fixed Android/QEMU compatibility fields, preserves typed domain values, and fails closed before any QEMU or mutable filesystem side effect.
- The APK/package test proves the exact profile JSON and checked-in guest-init sources required by those profiles are present.
- Artifact publication, image listing, and runtime consumption of active manifests use one strict versioned contract with exact fields, digest, size, immutable relative path, and root-containment checks.
- Built-in legacy artifact fallback is isolated behind that artifact repository and cannot weaken active-manifest parsing.
- H01 upload behavior and the hardened public HTTPS importer retain their existing authentication, SSRF, idempotency, digest, size, recovery, and atomic-publication invariants.
- Existing typed QEMU command snapshots and profile/guest qualification tests remain green.
- No result is represented as physical Android evidence, and no base-MVP gate changes status.

## Required checks

```sh
make validate
make test-jvm
make test-android
make test-guest
python3 tools/agents/verify-scope.py F01
```

GitHub CI must also pass APK packaging, profile-asset verification, signature verification, 16 KiB alignment, and candidate-artifact upload.

## Phase-end verification

Before marking F01 merge-ready:

1. Check every acceptance criterion against code, tests, and package evidence; record the result in `docs/research/experiments/F01.md`.
2. Search production Kotlin for the three profile IDs and confirm remaining occurrences are identifiers/tests/compatibility checks, not duplicated definitions.
3. Search for direct parsing of artifact manifest JSON and justify or remove every parser outside the selected contract adapter.
4. Run the required checks and the full applicable CI workflow.
5. Re-evaluate H02 and H03 at the next phase boundary. Split, narrow, reorder, or remove them based on what F01 actually proves.

## Handoff

Report commit SHA(s), exact checks, package evidence, profile/manifest differences removed, unavailable checks, deferred items, and the smallest next blocker. Do not activate the next phase merely because code exists; activate it only after the phase-end verification passes.
