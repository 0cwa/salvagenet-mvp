# Foundation and device-validation handoff

The repository is a **software-qualified device-lab candidate**, not a completed software implementation and not a validated MVP. H01 and H04 are merged, F01 is the sole active foundation task, H02/H03 are queued for re-review, and 10 of 20 base gates still require physical/live-network evidence.

## Current execution order

1. Complete F01 so checked-in profile JSON and one artifact-manifest contract are the exact production inputs.
2. At the next phase boundary, re-evaluate and narrow/split H02 and H03 rather than starting their stale packets automatically.
3. Use the existing one-phone HIL runner for the physical vertical slice.
4. Bind final gate evidence to one exact candidate commit and APK.

A physical D01/HIL smoke may run during F01 when a device is available and is useful diagnostic evidence. Because F01 changes production profile resolution, do not treat an earlier APK as the final D07 candidate without re-running the relevant scenarios.

## Phase handoff rule

At the start of a phase, verify the active packet's prerequisites, allowed paths, and acceptance criteria against current `main`. At the end, check every acceptance and phase-exit criterion against tests/package evidence before activating the next phase. Record unavailable physical checks honestly.

## One-time host and phone preparation

Run host setup yourself; do not give a coding agent root credentials:

```sh
sudo tools/bootstrap/ubuntu-root-setup.sh
# Log out/in once for docker + plugdev + kvm group changes.
tools/bootstrap/install-go.sh
tools/bootstrap/install-android-sdk.sh
source "$HOME/.config/nodehost/env.sh"
yes | sdkmanager --licenses
```

Connect one dedicated ARM64 Android phone, enable USB debugging, and accept its RSA prompt.

## Prepare disposable Headscale/controller state

```sh
cp lab/headscale/.env.example lab/headscale/.env
# Set HEADSCALE_PUBLIC_URL to a URL reachable by the phone.
make lab-up
make lab-keys
make lab-status

cp tests/hil/config.example.json .local/hil.json
# Set the exact ADB serial, node names, guest SSH target, and artifact-upload/import files.
```

Complete enrollment and Android VPN approval once for persistent development mode. Live keys remain only in ignored lab/controller files.

## Establish the exact APK

Use a green CI artifact when possible, or build locally with the same checks:

```sh
make validate
make test-jvm
make test-android
make test-guest
make hil-doctor HIL_BUILD=1
```

Do not transfer a pass from a different source commit, profile package, or APK.

## Run physical scenarios

```sh
make hil-smoke HIL_BUILD=1
make hil-mvp
make hil-resilience
# or: make hil-all HIL_BUILD=1
```

The runner writes ignored evidence under `.local/hil-runs/`. `hil-resilience` leaves reboot skipped unless `.local/hil.json` explicitly enables it.

## Promote evidence and update status

Review redaction and assertions, then use the existing evidence tooling to promote the relevant run into `evidence/gates/`.

```sh
make mvp-status
make validate
```

A fake, emulator, host-QEMU, package build, or code review cannot close a physical gate. USB/AOA networking remains unscheduled until every B01–B20 gate is PASS.

## Authorization boundaries

The agent may use the repository, existing Docker/Podman socket, authorized ADB device, SDK/NDK, and ignored lab/controller files needed by the scenario. Do not provide production Headscale credentials, release-signing keys, unrelated private keys, or general root access.
