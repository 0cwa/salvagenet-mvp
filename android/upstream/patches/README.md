# Podroid downstream patch series

`series` is the ordered, reviewable delta from the exact upstream commit in
`../podroid.lock` to the tracked `android/podroid/` tree.

The series separates the downstream concerns:

- `0001` is the narrow SalvageNet workspace and external composition hook;
- `0002` records inherited node startup, notification, and backup-security changes;
- `0003` records Android API compatibility, Compose resource, and enrollment UI changes;
- `0004` records pointer-input cleanup and terminal unit-test configuration;
- `0005` records Podman-or-Docker native build support.

SalvageNet-owned composition, runtime preparation, and package verification
live outside the subtree. New project behavior should remain in sibling modules
or external integration files rather than expanding these historical patches.

`make podroid-verify` fetches the locked commit, applies every listed patch, and
compares every tracked file and executable bit with `android/podroid/`. An
unlisted patch, an untracked downstream edit, or a stale patch fails the check.
When that CI gate fails, it also uploads the exact current patch drift for review.

Do not edit the vendored tree and the patch independently. Change the external
integration first where possible; otherwise refresh the relevant patch in the
same PR.
