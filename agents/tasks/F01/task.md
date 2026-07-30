# F01 — Canonical artifact and profile resolution

## Status

**IN PROGRESS — post-exit hardening.** Initial implementation head `a343b3dc283d22fe49bbef3caefb6e05f446f4a8` passed Actions run `30533830617`, but focused review found that the bare-file legacy fallback was not restricted to the pinned Podroid qualification inputs. The fix and regression test now require a new full workflow.

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
- Manifest producers and consumers were inventoried in `docs/research/experiments/F01.md`.
- Built-in Podroid assets may retain bare-file plus `.sha256` storage only for `podroid-kernel`, `podroid-initramfs`, and `podroid-alpine-squashfs`. Every other profile artifact requires a valid active manifest.
- H02, H03, qcow2 semantic changes, native source builds, UI rewrites, controller replacement, process isolation, and USB remain out of scope.

## Allowed paths

See `allowed-paths.txt`. Phase status and roadmap updates are included only to record this task's verified result; implementation scope remains inside the selected profile/artifact boundary.

## Acceptance criteria

- [x] Packaged, build-validated JSON is the sole production source for `alpine-direct-qualification`, `ubuntu-2404-arm64-uefi`, and `k3s-worker-lab`.
- [x] Android production code no longer duplicates complete profile definitions in a Kotlin `when` or equivalent mirror.
- [x] Profile loading is bounded, rejects unknown fields and unsupported contracts, validates fixed Android/QEMU compatibility fields, preserves typed domain values, and fails closed before QEMU or mutable disk effects.
- [x] The APK/package test proves the exact profile JSON, schema, index, and rendered guest-init assets required by those profiles are present.
- [x] Artifact publication, image listing, cleanup, installed checks, and runtime consumption of active manifests use one strict versioned contract with exact fields, digest, size, immutable relative path, and root-containment checks.
- [~] Legacy fallback is restricted to the three pinned Podroid qualification artifacts; updated runtime tests and full CI are pending.
- [x] H01 upload behavior and the hardened public HTTPS importer retain their authentication, SSRF, idempotency, digest, size, recovery, cancellation, and atomic-publication invariants on the previously validated implementation head.
- [~] Typed QEMU, profile, guest, Android, package, signature, and alignment checks require revalidation on the hardened head.
- [x] No result is represented as physical Android evidence, and no base-MVP gate changes status.

## Required checks

The hardened head must pass:

```sh
make validate
make test-jvm
make test-android
make test-guest
python3 tools/agents/verify-scope.py F01
```

GitHub CI must also pass APK packaging, canonical profile-asset verification, Podroid runtime verification, signature verification, 16 KiB alignment, and candidate-artifact upload.

Previous candidate evidence from the superseded implementation head remains useful but is not final:

```text
head: a343b3dc283d22fe49bbef3caefb6e05f446f4a8
run: 30533830617
apkSha256: ab3d3b841d481088d2f4b8e8800abaa73884a17051484853a8d2060246527928
hardwareValidated: false
```

## Phase-end verification

Before marking F01 merge-ready again:

1. Check every acceptance criterion against the hardened code, tests, and package evidence; update `docs/research/experiments/F01.md`.
2. Confirm production Kotlin contains no complete profile mirror and no direct active-manifest parser outside `ArtifactManifestStore`.
3. Confirm non-Podroid bare files cannot satisfy Ubuntu/AAVMF profile resolution.
4. Run the required checks and the full applicable CI workflow.
5. Reconfirm the H02/H03 split and activate only guest boot qualification after merge.

## Handoff

Merge only the exact final tested documentation head. After merge, record the merge SHA, archive F01 as merged, and activate one narrowly scoped guest-boot qualification task. Keep guest mesh and both emulator tasks queued until their stated prerequisites pass. No physical gate changes status.