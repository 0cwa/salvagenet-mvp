# F01 — Canonical artifact and profile resolution

## Status

**MERGED** at `246d551ca7e691a0319a4b30e29d6e4905cd9910`.

Final head `31dcd75199928b7887132a1429392266388c0b60` passed Actions run `30549498423`, including repository/contracts, JVM/domain, Android tests and lint, guest/profile qualification, APK construction, exact canonical asset verification, Podroid runtime verification, signature, 16 KiB alignment, and candidate upload.

## Outcome

Checked-in VM profile JSON and one strict artifact-manifest contract became the Android production inputs. The complete Kotlin profile mirror was removed, exact profile/schema/index/guest-init assets are packaged and verified, and artifact publication, listing, cleanup, installed checks, and runtime consumption share `ArtifactManifestStore`.

## Phase-start review

Historical. The phase started from `9e497bd33ad8c8a05e2cda9d0ba2e9ffd7a673f7` after H01 and H04 merged. Profile and artifact resolution were kept together because both source-of-truth problems met at the Android storage/resource boundary.

## Compatibility policy

The merged implementation included a pre-release Ubuntu/AAVMF migration path. The project subsequently clarified that unreleased alpha state does not warrant compatibility code; removal or correction belongs to a separate scoped cleanup rather than extending this merged packet.

## Allowed paths

Historical packet; see `allowed-paths.txt` for the paths authorized during F01. It grants no current work authorization.

## Acceptance criteria

- [x] Packaged, build-validated JSON became the production source for the three qualified profiles.
- [x] Android production code stopped duplicating complete profile definitions.
- [x] Profile loading became bounded and fail-closed before QEMU or mutable disk effects.
- [x] APK verification proved exact profile JSON, schema, index, and required guest-init assets.
- [x] Active artifact publication and consumption converged on one strict manifest contract.
- [x] Artifact preparation reused one verified source resolution per preparation and verified copied bytes.
- [x] H01 upload and public HTTPS-import security invariants remained green.
- [x] No physical-device acceptance claim or base-MVP gate change was made.

## Required checks

The final merged head passed the complete GitHub workflow in Actions run `30549498423`.

## Phase-end verification

F01 was merged, its merge SHA is recorded in `agents/task-registry.json`, and the next active phase was narrowed to deterministic Ubuntu guest-boot qualification. Guest mesh and emulator work remain separate queued decisions.

## Handoff

Historical provenance only. Do not reopen or extend F01 silently. New cleanup, compatibility, profile-contract, or guest-qualification work requires a new or explicitly reactivated scoped packet.
