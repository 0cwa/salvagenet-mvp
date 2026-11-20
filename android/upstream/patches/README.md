# Podroid downstream patch series

`series` is the ordered, reviewable delta from the exact upstream commit in
`../podroid.lock` to the tracked `android/podroid/` tree.

The series separates the downstream concerns:

- `0001` is the narrow SalvageNet workspace and external composition hook;
- `0002` records inherited node startup, notification, and backup-security changes;
- `0003` retains Android API compatibility and enrollment, hides the optional
  UML choice because SalvageNet does not package that backend, and removes the
  upstream boot toggle because node-shell owns the boot policy;
- `0004` retains terminal unit-test configuration;
- `0005` retains Podman-or-Docker native build support, including the new upstream
  documentation staging and optional UML build commands;
- `0006` excludes upstream's new automation and debug execution registrations,
  including explicit-intent dispatch in the exported launcher Activity;
- `0007` starts the cancellation test's relay before cancelling it, avoiding a
  coroutine scheduling race while retaining both socket-closure assertions;
- `0008` keeps Home and Settings resource lookups aware of Compose configuration
  changes, including the new port-forward table limit message.

The v1.3.0 refresh drops obsolete backup-screen and X11 formatting hunks, while
adapting the still-required Home and Settings resource fixes to the refreshed
UI. The current queue is derived from the exact v1.3.0 tag; it is not a partial
application of the v1.2.6 patches.

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
