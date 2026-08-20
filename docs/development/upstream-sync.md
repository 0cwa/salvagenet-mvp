# Podroid import and upstream synchronization

## Model

`android/podroid/` is a pinned, squashed Git subtree. The Makefile is only the
maintainer-facing entry point; `tools/vendor/podroid.py` owns lock validation,
import, update, patch application, diffing, and verification.

Squashing keeps the superproject history readable. It preserves **upstream
provenance** through the full commit SHA, repository, release, subtree metadata,
and ordered patch series; it does not preserve every upstream commit as a local
commit.

SalvageNet-owned Android modules and build/package logic remain outside the
subtree. The vendored app contains one narrow hook to
`android/podroid.integration.gradle.kts`.

## Commands

```sh
make podroid-import   # clean initial import, then apply the patch series
make podroid-update   # subtree-pull the commit currently recorded in the lock
make podroid-verify   # fetch upstream and reproduce the tracked subtree exactly
make podroid-diff     # show uncaptured differences
```

`make import-podroid` and `make wire-podroid` remain compatibility aliases.
Normal builds and offline repository validation do not contact GitHub.

## Lock and patch contract

`android/upstream/podroid.lock` records:

- the HTTPS upstream repository;
- a full 40-character commit SHA and associated release;
- the fixed subtree destination and import method;
- the ordered patch-series path;
- capture/verification dates and the verified commit message.

`android/upstream/patches/series` lists every patch in application order.
`make podroid-verify` creates a temporary checkout of the exact upstream commit,
applies that series, and compares its complete file set, contents, and executable
bits with the tracked Podroid tree. This makes uncaptured downstream edits a hard
failure rather than upgrade folklore.

## Initial import

Run on a clean worktree whose scaffold does not yet contain `android/podroid/`:

```sh
make podroid-import
```

The subtree command creates the vendor commit. The ordered patches remain as
working-tree changes so the adaptation can be reviewed and committed separately.

## Upstream update

Use a dedicated branch and do not mix the bump with feature work.

1. Update the lock's commit, release, dates, and verified message.
2. Run `make podroid-update`; this creates the squashed subtree merge.
3. Resolve upstream merge conflicts without adding new product behavior.
4. Refresh the ordered patch series against the new baseline.
5. Run `make podroid-verify` until the reconstructed tree is exact.
6. Run Podroid baseline, JVM, Android/lint, guest, and package checks.
7. Commit the upstream vendor merge and adaptation/patch refresh separately.
8. Record relevant upstream QEMU, native-build, networking, and lifecycle
   changes in the experiment/source registers.

A failed post-pull verification is expected when the old patch no longer
represents the new baseline; it is not permission to skip the patch refresh.

## Extraction and licensing

When moving Podroid code into sibling modules, retain the original path and
pinned commit in provenance documentation. Prefer wrappers or delegation before
broad moves during the MVP.

Podroid is GPLv2-licensed and the APK links SalvageNet modules into the app.
Before distributing release APKs, complete and document the repository-wide
GPLv2 compatibility, notices, corresponding-source, and modification-notice
review. The vendoring workflow records provenance but does not itself settle
that release-policy decision.
