# End-to-end validation instructions

- State the environment class in every result: fake, JVM/Robolectric, emulator, host-QEMU, or physical Android. Only physical Android closes B02/B07–B13/B16–B17.
- Bind each run to one source commit, one exact APK, controller configuration hash, Headscale lab version, and device-facts record.
- Verify separate host and guest mesh identities and test both direct/relay paths when available.
- The normal path uses guest SSH; the recovery test intentionally disables guest mesh and uses only the authenticated host tunnel.
- Re-running an idempotency key with different content must fail; older desired generations must not replace newer state.
- Evidence scripts fail closed on missing observations. Manual continuation steps must not automatically update the ledger.
- Never include live enrollment/auth keys, controller capabilities, private SSH keys, or full VM disks in committed artifacts.
