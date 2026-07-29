# Physical-device test instructions

- These tests produce acceptance evidence, not informal smoke-test notes.
- Record source commit, exact APK SHA-256/signature, device manufacturer/model/API/ABI/page size, power state, and test start/end times.
- Never mark a gate `PASS` from code inspection, JVM tests, emulator behavior, or an unrecorded manual observation.
- Capture process counts, listener addresses, QMP status, service state, and redacted logcat for lifecycle claims.
- ADB commands must target one explicitly selected serial and fail when multiple devices are connected.
- Reboot tests distinguish locked boot, first unlock, service recreation, and desired-state convergence.
- Store raw sensitive output only under ignored `.local/`; committed evidence contains hashes, bounded excerpts, and redaction notes.
- Exit 77 means environment/hardware blocked, not pass.
