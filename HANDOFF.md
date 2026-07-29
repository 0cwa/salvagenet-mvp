# Human-to-device-validation handoff

The T00–T08 overnight software implementation cycle is complete. The repository is now a **device-lab candidate**. The acceptance ledger still requires an authorized ARM64 Android device, live Headscale connectivity, a real QEMU/Ubuntu boot, guest SSH, recovery SSH, and lifecycle/reboot evidence.

Use [`agents/device-validation-goal.md`](agents/device-validation-goal.md), not the historical overnight implementation goal, for the next run.

## 1. One-time host authorization

Run these as the human operator; do not give an agent root credentials:

```sh
sudo tools/bootstrap/ubuntu-root-setup.sh
# Log out/in once for docker + plugdev + kvm group changes.
tools/bootstrap/install-go.sh
tools/bootstrap/install-android-sdk.sh
source "$HOME/.config/nodehost/env.sh"
yes | sdkmanager --licenses
```

Authorize one ARM64 Android phone with ADB, accept the device RSA prompt, then verify:

```sh
make doctor
make device-facts
adb devices -l
```

The device must appear as `device`, not `unauthorized`.

## 2. Start the disposable Headscale laboratory

```sh
cp lab/headscale/.env.example lab/headscale/.env
# Set HEADSCALE_PUBLIC_URL to a URL reachable by the phone.
make lab-up
make lab-keys
make lab-status
```

Confirm the phone can reach the Headscale health URL. Live keys remain only in ignored files under `lab/headscale/secrets/`.

## 3. Establish the exact software candidate

Use a green GitHub Actions artifact when available. Record its source commit and SHA-256 before installation. A locally built candidate must run the same checks:

```sh
make validate
make test-jvm
make test-android
make test-guest

cd android/podroid
./gradlew :app:assembleDebug :mesh-tailscale:assembleRelease :app:verifyPodroidPackaging
```

Do not carry a `PASS` from a different APK or source commit into physical evidence.

## 4. Run the device-validation cycle

Follow [`docs/roadmap/device-validation.md`](docs/roadmap/device-validation.md) in order:

```text
D01  APK-native Alpine/QEMU boot and real QMP readiness
D02  host Tailscale/Headscale and authenticated Host API
D03  Ubuntu UEFI deployment, guest mesh, and ordinary SSH
D04  host-mediated recovery SSH
D05  Activity/service/process/reboot/controller-offline continuity
D06  only bounded corrections demonstrated by those tests
D07  one-commit/one-APK MVP evidence seal
```

For each stage, read the nearest `AGENTS.md` under `tests/device`, `tests/e2e`, and the component being debugged.

## 5. Evidence rules

A physical gate record must include:

- exact source commit and APK SHA-256;
- device manufacturer/model, API level, ABI, page size, and relevant power policy;
- exact command or scripted procedure;
- redacted logs/artifacts;
- automated versus manually observed fields;
- `PASS`, `FAIL`, or `BLOCKED-HARDWARE` without inference from unit/emulator tests.

Regenerate the public status after any ledger update:

```sh
make mvp-status
make validate
```

USB/AOA networking remains unscheduled until every B01–B20 gate is `PASS`.

## Authorization boundaries

The validation agent may use the repository, its worktrees, the already authorized Docker/Podman socket, the authorized ADB device, the installed Android SDK/NDK, and ignored laboratory keys needed for the active stage.

Do not provide production Headscale API keys, APK release-signing keys, unrelated SSH/private keys, or root credentials. Do not commit unfiltered logcat, auth keys, controller capabilities, guest disks, or enrollment bundles.
