# F01 — Canonical artifact and profile resolution

Status: **MERGED** at `246d551ca7e691a0319a4b30e29d6e4905cd9910`.

F01 is historical provenance, not active work authorization. Its exact final head `31dcd75199928b7887132a1429392266388c0b60` passed the complete workflow in Actions run `30549498423`; the downloaded APK matched the commit-bound evidence files.

The result makes checked-in profile JSON and one strict active artifact-manifest contract the production source of truth. Non-Podroid artifacts require active manifests. Because the application has no deployed pre-F01 installations, no Ubuntu/AAVMF compatibility migration is retained.

The active task is H02A. Generate its context with:

```sh
make context TASK=H02A
```
