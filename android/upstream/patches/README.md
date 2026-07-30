# Podroid downstream patch series

`series` is the ordered, reviewable delta from the exact upstream commit in
`../podroid.lock` to the tracked `android/podroid/` tree.

The current patch is intentionally narrow:

- include SalvageNet sibling Gradle modules;
- append the canonical workspace property block;
- apply `android/podroid.integration.gradle.kts` from the Podroid app.

SalvageNet-owned composition, runtime preparation, and package verification
live outside the subtree. New project behavior should remain in sibling modules
or external integration files rather than expanding this patch.

`make podroid-verify` fetches the locked commit, applies every listed patch, and
compares every tracked file and executable bit with `android/podroid/`. An
unlisted patch, an untracked downstream edit, or a stale patch fails the check.

Do not edit the vendored tree and the patch independently. Change the external
integration first where possible; otherwise refresh the patch in the same PR.
