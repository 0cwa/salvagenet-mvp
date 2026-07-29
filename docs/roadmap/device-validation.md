# Device-validation development cycle

The overnight T00–T08 cycle produced an integrated software candidate. The next cycle is evidence-driven and runs on the exact CI-built APK. Do not reuse `PASS` from unit/emulator tests as physical evidence.

## D00 — Repository and release truth

- Generated `docs/STATUS.md` matches the acceptance ledger.
- CI pins Java, Go, Android SDK/NDK and runs the complete automated build.
- CI uploads the exact APK, SHA-256, size, signature/alignment result, source commit, and explicit `hardwareValidated: false` evidence.
- Historical scaffold files are not presented as current status.

## D01 — APK-native QEMU boot

Close B02.

1. Record device facts and APK SHA-256.
2. Install the exact CI artifact.
3. Start the Alpine direct-kernel profile.
4. Prove one QEMU process, launcher/nativeLibraryDir execution, real QMP greeting/capabilities/query-status, bounded diagnostics, and clean stop/restart.
5. Attach redacted logcat, process list, QMP status, and gate record.

Stop and fix only the smallest demonstrated platform issue before proceeding.

## D02 — Host mesh and Host API

Close B08 and B09.

1. Import enrollment and approve Android VPN once.
2. Join the disposable Headscale deployment as the host identity.
3. Test direct and relayed reachability to the authenticated HTTPS Host API.
4. Restart the service and change Wi-Fi/cellular path where available.
5. Record memory, wakeups, listener address, certificate identity, and key-erasure evidence.

This task decides whether the current embedded-listener architecture is viable. Do not pre-emptively replace Ktor or libtailscale.

## D03 — Ubuntu deployment and guest mesh

Close B10, B11, and B12.

1. Deliver the pinned Ubuntu and firmware artifacts through a bounded trusted path.
2. Apply a desired generation remotely.
3. Prove UEFI boot, QMP readiness, NoCloud retrieval, key-only SSH, separate guest Headscale identity, and ordinary SSH.
4. Inspect cloud-init logs and guest disk for deleted one-use enrollment material.
5. Run the K3s qualification profile without joining a cluster.

## D04 — Recovery path

Close B13.

- Disable or break guest mesh after a successful boot.
- Connect through the authenticated Host API recovery tunnel to the loopback-only QEMU SSH forward.
- Verify session count, idle/byte/overall limits, cross-runtime denial, and recovery after tunnel interruption.

## D05 — Lifecycle and offline reliability

Close B07, B16, and B17.

- destroy/rotate/swipe the Activity;
- kill/restart the service and application process;
- crash QEMU during an operation;
- reboot, delay first unlock, then unlock;
- keep the controller offline and confirm the VM continues;
- reconnect and verify desired/observed generation and one-process invariants.

Every result records device/OEM/API level, power policy, exact APK, source commit, and whether the check was automated or manually observed.

## D06 — Bounded corrections

Apply only findings demonstrated by D01–D05. Re-run the affected automated suite and all previously passing physical gates. Update the debt register rather than hiding unresolved findings in code comments.

## D07 — MVP seal

- Every B01–B20 gate is `PASS` with evidence.
- A clean CI build from one source commit produces the tested APK.
- APK SHA/signature/alignment match the release evidence.
- README and `docs/STATUS.md` regenerate from the final ledger.
- The release is titled **MVP** only after the physical evidence seal.
- Only then may the MVP+ USB task enter executable scope.
