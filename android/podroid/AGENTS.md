# Imported Podroid island instructions

- Treat this subtree as imported upstream code with local composition patches, not the default home for NodeHost behavior.
- Prefer wrappers and sibling modules under `android/modules/`; broad moves or rewrites require an explicit upstream-sync/extraction task.
- Preserve nativeLibraryDir executable packaging, launcher-first argv, dedicated spawn/reap behavior, Unix sockets, and packaging verification.
- Every copied or moved upstream file records its original path and pinned commit.
- Do not update the Podroid snapshot and implement a feature in the same commit.
- After any change here, run the Podroid packaging verification and the smallest affected upstream/app test before NodeHost tests.
- Never add live keys, downloaded mutable binaries, arbitrary QEMU arguments, or user-controlled shell execution.
