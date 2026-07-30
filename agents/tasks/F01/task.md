# F01 — Canonical artifact and profile resolution

## Status

**PLANNED — sole active task in phase `foundation-1`.**

## Outcome

Make the checked-in VM profile JSON and the project artifact-manifest contract the exact production inputs used by the Android runtime, so later host-QEMU, emulator, and physical tests exercise the same configuration semantics.

## Why this is foundational

The repository says profile JSON is canonical, but `AndroidQemuProfileStorage` currently constructs the three production profiles in Kotlin and independently parses artifact manifests. A lab can therefore pass against checked-in profile data while the APK executes a different mirror. Adding more E2E layers before removing that split source of truth would increase debugging ambiguity.

## Prerequisites

- H01 merged at `60d0394e25cc84f8ea0dcc39f62a349c17171b2b`.
- H04 merged at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`.
- Current profile schemas and examples pass `make validate`.

## Phase-start review

Before implementation:

1. Run `make dev-plan` and `make validate` on current `main`.
2. Compare every field in the three checked-in profile JSON files with the Kotlin production mirror and record all differences in `docs/research/experiments/F01.md`.
3. Identify every producer and consumer of `nodehost-artifacts/*.manifest.json` and confirm the intended shared contract.
4. Re-read this packet and narrow it if implementation discovery shows that profile loading and manifest unification cannot remain one cohesive change.
5. Do not begin H02, H03, qcow2 semantic changes, native source builds, UI rewrites, or USB work in this task.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff and a phase-plan review.

## Acceptance criteria

- Packaged, schema-validated JSON is the sole production source for `alpine-direct-qualification`, `ubuntu-2404-arm64-uefi`, and `k3s-worker-lab`.
- Android production code no longer duplicates complete profile definitions in a Kotlin `when` or equivalent mirror.
- Profile loading is bounded, rejects unknown fields/unsupported versions, preserves typed domain values, and fails closed before any QEMU or filesystem side effect.
- The APK/package test proves the exact profile JSON and trusted guest-init assets required by those profiles are present.
- Artifact publication, image listing, and runtime consumption use one strict versioned manifest contract with exact fields, digest, size, immutable relative path, and root-containment checks.
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
