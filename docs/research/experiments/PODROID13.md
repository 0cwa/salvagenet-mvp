# Podroid v1.3.0 upstream sync

## Scope and authorization

The user explicitly requested this dedicated upstream sync, a pull request, and
incremental pushes on 2026-11-20. This is bounded maintenance of the imported
Podroid source, downstream patch queue, matching runtime inputs, and checks.
It does not activate another product phase or change an acceptance gate.

## Immutable inputs

- Starting SalvageNet `main`: `8e0047516a94565dc082fbce4582d9b49a843884`.
- Previous source: `ExTV/Podroid` commit
  `8ecfefaa3459b7e84c3d6e52c57e8005e289e8e3`, release `v1.2.6`.
- Selected source: latest stable release [v1.3.0](https://github.com/ExTV/Podroid/releases/tag/v1.3.0),
  tag commit `d5f7210182db9fbbee3ce6780ddd4b3e520e304b`.
- Upstream `main` observed at `e3fc1befa3c135d28bf8d40e3c2264d93fea87ef`;
  its two commits after the release change documentation only.
- Matching release APK: `Podroid-v1.3.0-release.apk`, asset `729305941`,
  size `325165405` bytes, published SHA-256
  `705d7f400e32d8e0b0f49b52c97dc25cd20bc8719bcecc1d24eb070b4456d6a3`.

Source and runtime remain pinned to the same release. The v1.3.0 import brings
upstream's QEMU 11.1.2 and Linux 7.3 inputs; adopting upstream's experimental UML
or AVF backend as a SalvageNet runtime is outside this sync.

## Review questions

1. Which historical patches remain necessary, have landed upstream, or need
   adaptation to the current source?
2. Can the complete imported tree be reconstructed from the release commit plus
   the refreshed patch queue, including modes and generated-source exclusions?
3. Do the pinned APK contents preserve the executable-in-`nativeLibraryDir`
   launcher, native dependencies, and direct-kernel qualification assets?
4. Do newly imported automation entry points preserve SalvageNet's authenticated
   single-supervisor control boundary?
5. Do source tests, Android build/lint, package integrity, signature, and 16 KiB
   alignment checks pass for the exact PR head?

## Initial evidence

- `make validate`: PASS on the starting `main`.
- `make dev-plan`: repository and guest checks available locally; Android SDK is
  unavailable in this workspace. GitHub Actions will run the Android gates.
- Existing compatibility PR [#100](https://github.com/0cwa/salvagenet-mvp/pull/100)
  remains separate. Its last source canaries stop at patch conflicts, and its
  regular source-reconstruction check detects uncaptured patch drift. Those runs
  do not establish compatibility with a newer Podroid release.

## Outcome

IN PROGRESS. Record the final source, package, and physical-validation results
here as they become available. No new Android-device or acceptance claim is made.
