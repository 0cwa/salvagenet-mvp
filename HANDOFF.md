# Guest-boot and device-validation handoff

The repository is a **software-qualified device-lab candidate**, not a validated MVP. F01, H01, and H04 are merged. H02A is the sole active software-preflight task. H02B and H03 remain queued, and 10 of 20 base gates still require physical or live-network evidence.

## Current execution order

1. Complete H02A: canonical Ubuntu profile and artifact identity, UEFI/QMP, NoCloud, key-only loopback SSH, restart, secret-residue inspection, and bounded host-QEMU evidence.
2. At the H02A phase boundary, decide whether guest mesh qualification is still the next highest-value uncertainty. Do not activate H02B automatically.
3. Reassess emulator work only if a remaining Android lifecycle ambiguity justifies its setup and maintenance cost.
4. Use the existing one-phone HIL runner for the physical vertical slice when hardware is available.
5. Bind final gate evidence to one exact candidate commit and APK.

F01 merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910`. Its final validated head `31dcd75199928b7887132a1429392266388c0b60` passed Actions run `30549498423` and produced the commit-bound candidate recorded in `agents/task-registry.json`.

Because there are no deployed pre-F01 installations, Ubuntu and AAVMF artifacts always require active manifests. No compatibility migration path is retained.

## Phase handoff rule

At the start of a phase:

1. update from current `main`;
2. run `make dev-plan` and `make validate`;
3. verify the active packet's prerequisites, allowed paths, and acceptance criteria against current implementation;
4. activate only the smallest task that resolves the next uncertainty;
5. state what evidence the phase cannot claim.

At the end of a phase:

1. check every task acceptance criterion and phase exit criterion against actual evidence;
2. run the task checks and complete applicable CI;
3. record implemented, tested, merge-ready, merged, host-qualified, and physically validated states separately;
4. update the merge SHA and evidence identity;
5. replan queued tasks from the result instead of preserving stale scope.

## H02A host preparation

H02A is a Linux host-QEMU qualification phase. It does not require a phone or Headscale.

Run host setup yourself; do not give a coding agent root credentials:

```sh
sudo tools/bootstrap/ubuntu-root-setup.sh
# Log out/in once for docker + plugdev + kvm group changes where applicable.
tools/bootstrap/install-go.sh
tools/bootstrap/install-android-sdk.sh
source "$HOME/.config/nodehost/env.sh"
```

Then inspect the active packet and local capability report:

```sh
cat agents/tasks/H02A/task.md
make context TASK=H02A
make dev-plan
make validate
make qemu-lab-e2e
```

H02A evidence must remain under `.local/qemu-lab/`, identify its class as `host-qemu`, and state both `androidHardwareValidated: false` and `physicalGateEligible: false`.

## Later physical preparation

When a dedicated ARM64 Android phone is available, enable USB debugging and accept its RSA prompt. Prepare disposable Headscale/controller state only for H02B or physical HIL work:

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

## Establish the exact APK for physical work

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

Review redaction and assertions before promoting relevant evidence into `evidence/gates/`, then regenerate status:

```sh
make mvp-status
make validate
```

A fake, emulator, host-QEMU, package build, or code review cannot close a physical gate. USB/AOA networking remains unscheduled until every B01–B20 gate is PASS.

## Authorization boundaries

The agent may use the repository, existing Docker/Podman socket, SDK/NDK, and ignored lab files required by the active scenario. A later physical agent may use an explicitly authorized ADB device. Do not provide production Headscale credentials, release-signing keys, unrelated private keys, or general root access.
