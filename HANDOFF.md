# Human-to-device-validation handoff

The software implementation cycle is complete. The repository is a **device-lab candidate**. Physical validation now uses one small runner rather than a collection of manual scripts or a device-farm project.

## 1. One-time host and phone preparation

Run host setup yourself; do not give the coding agent root credentials:

```sh
sudo tools/bootstrap/ubuntu-root-setup.sh
# Log out/in once for docker + plugdev + kvm group changes.
tools/bootstrap/install-go.sh
tools/bootstrap/install-android-sdk.sh
source "$HOME/.config/nodehost/env.sh"
yes | sdkmanager --licenses
```

Connect one dedicated ARM64 Android phone, enable USB debugging, and accept its RSA prompt.

## 2. Prepare the existing Headscale/controller state

```sh
cp lab/headscale/.env.example lab/headscale/.env
# Set HEADSCALE_PUBLIC_URL to a URL reachable by the phone.
make lab-up
make lab-keys
make lab-status

cp tests/hil/config.example.json .local/hil.json
# Set the exact ADB serial, node names, guest SSH target, and artifact-import files.
```

Complete enrollment and Android VPN approval once for the persistent development mode. Live keys remain only in ignored lab/controller files.

## 3. Establish the exact APK

Use a green CI artifact when possible, or build locally with the same checks:

```sh
make validate
make test-jvm
make test-android
make test-guest
make hil-doctor HIL_BUILD=1
```

Do not transfer a pass from a different source commit or APK.

## 4. Run the physical scenarios

```sh
make hil-smoke HIL_BUILD=1
make hil-mvp
make hil-resilience
# or: make hil-all HIL_BUILD=1
```

The runner writes ignored evidence under `.local/hil-runs/`. `hil-resilience` leaves reboot skipped unless `.local/hil.json` explicitly enables it.

## 5. Promote evidence and update status

Review redaction and assertions, then use the existing evidence tooling to promote the relevant run into `evidence/gates/`.

```sh
make mvp-status
make validate
```

USB/AOA networking remains unscheduled until every B01–B20 gate is `PASS`.

## Authorization boundaries

The agent may use the repository, existing Docker/Podman socket, authorized ADB device, SDK/NDK, and ignored lab/controller files needed by the scenario. Do not provide production Headscale credentials, release-signing keys, unrelated private keys, or general root access.
