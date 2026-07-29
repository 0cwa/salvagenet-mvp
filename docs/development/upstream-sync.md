# Podroid import and upstream synchronization

## Initial import

`android/upstream/podroid.lock` pins the repository and commit. `make import-podroid` uses Git subtree so imported history/content is available under `android/podroid/` while this superproject owns sibling modules.

## Wiring

`make wire-podroid` applies an idempotent settings fragment, appends centralized node-host versions, and adds the narrow `:node-shell` dependency. It writes marker comments so repeated runs are safe.

## Future upstream sync

1. update the lock on a dedicated task/branch;
2. import the new upstream commit;
3. run Podroid baseline tests before resolving node-host integration;
4. compare QEMU command snapshots and native build changes;
5. document migrated upstream fixes in the experiment register;
6. do not mix upstream sync with feature work.

## Extraction policy

When moving Podroid code into sibling modules, retain file history where practical and add a provenance header containing the original path and pinned commit. Prefer wrappers/delegation before broad moves during the MVP night.
