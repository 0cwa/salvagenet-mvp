# Podroid v1.3.0 upstream sync

## Scope and authorization

The user explicitly requested this dedicated upstream sync, a pull request, and
incremental pushes on 2026-11-20. This is bounded maintenance of the imported
Podroid source, downstream patch queue, matching runtime inputs, and checks.
It does not activate another product phase or change an acceptance gate.

## Immutable inputs

- Starting SalvageNet `main`: `8e0047516a94565dc082fbce4582d9b49a843884`.
- Previous source: `ExTV/Podroid` commit
  `8ecfefaa3459b7e84c3d6e52c57e8005e289e8e3`, release `v1.2.6`.
- Selected source: latest stable release [v1.3.0](https://github.com/ExTV/Podroid/releases/tag/v1.3.0),
  tag commit `d5f7210182db9fbbee3ce6780ddd4b3e520e304b`.
- Upstream `main` observed at `e3fc1befa3c135d28bf8d40e3c2264d93fea87ef`;
  its two commits after the release change documentation only.
- Matching release APK: `Podroid-v1.3.0-release.apk`, asset `729305941`,
  size `325165405` bytes, published SHA-256
  `705d7f400e32d8e0b0f49b52c97dc25cd20bc8719bcecc1d24eb070b4456d6a3`.

Source and runtime remain pinned to the same release. The v1.3.0 import brings
upstream's QEMU 11.1.2 and Linux 7.3 inputs; adopting upstream's experimental UML
or AVF backend as a SalvageNet runtime is outside this sync.

## Decisions and changes

The imported source advances by 126 upstream commits. The two newer upstream
`main` commits are documentation-only, so the stable tag preserves the existing
source/release/runtime provenance contract. The subtree remains squashed; source
and adaptation commits remain separately reviewable.

The seven ordered patches retain the workspace/build hooks, startup composition,
backup exclusions, notification permission guard, Android 26 stat compatibility,
enrollment row, terminal test configuration, and Podman/Docker build selection.
Obsolete resource and X11 formatting hunks were replaced by upstream's current
implementations. `make podroid-verify` reconstructs the complete tracked subtree,
including modes, from the exact tag and these patches.

Upstream's new exported VM receiver, launcher intent dispatch, control provider,
and debug UML harness are not registered in the SalvageNet APK. The inactive
upstream boot switch is removed, preserving node-shell's existing boot policy.
Source checks and a decoded packaged-manifest check guard this boundary. This
does not redesign the inherited local Podroid UI or make a new control API.

The optional UML choice is hidden because its five native payloads are not
packaged. Existing Auto/AVF/QEMU choices in the inherited UI remain unchanged;
SalvageNet's typed runtime remains QEMU. No new backend support is claimed.

The direct-kernel profile retains upstream's new `arm64.nompam` workaround.
Generic UEFI behavior is unchanged. A distinct upstream argv fixture now records
upstream paths and forwards separately from the production golden's scoped paths
and loopback recovery SSH. Android DNS propagation remains a separate change.

## Runtime input verification

The downloaded APK's size and SHA-256 match the published release metadata.
All 42 selected QEMU runtime entries exist exactly once and have verified sizes
and hashes. Four changed: QEMU, kernel, initramfs, and root filesystem. The
launcher, bridge, SLIRP, firmware, and keymaps are byte-identical to the old inputs.

`readelf -dW` confirms QEMU's sole packaged native dependency remains
`libslirp.so`; all other dependencies are Android system libraries. All four
locked native executables/libraries pass the existing AArch64/16 KiB ELF checks.
Offline runtime preparation and verification of the source APK both pass. These
checks establish input integrity, not the rebuilt APK or physical execution.

## Verification and evidence limits

| Check | Recorded result |
|---|---|
| `make validate` | PASS on starting main and the updated tree |
| `make podroid-verify` | PASS: exact v1.3.0 tree plus seven patches |
| `python3 tools/vendor/check-podroid-provenance.py` | PASS: release tag, SHA, and subject agree |
| QEMU fixture tests | PASS: four tests, including source-pin and adaptation agreement |
| Android control-surface tests | PASS: eight tests covering source and decoded manifests plus explicit Activity dispatch |
| `make test-guest` | PASS: guest-init, H02A contract, and K3s qualifier |
| Pinned runtime preparation/verification | PASS: 42 members and four AArch64/16 KiB ELF checks |
| Full Android, app/module tests, lint, rebuilt APK, signature/alignment | Exact-head GitHub Actions checks and artifacts on PR #101 |
| `make hil-doctor` | Exit 77: `.local/hil.json` is absent; no configured physical device |

The local workspace has no Android SDK. The normal Android workflow now runs
Podroid's app unit tests before the sibling suites and verifies the final APK's
manifest as well as its runtime/profile assets, signature, and ZIP alignment.
Consult [PR #101](https://github.com/0cwa/salvagenet-mvp/pull/101) for its current
head, check verdicts, and exact candidate identity. The CI-generated candidate
evidence records source SHA, APK digest, run ID, and `hardwareValidated: false`.

Local temporary storage must be outside the repository's `.local/` directory
when running the H02A confinement test; that test deliberately rejects external
temporary paths and accepts paths within `.local/`.

The first complete app-test run compiled the application and ran 479 tests;
only `AvfTcpRelayTest.cancellation_closes_both_idle_sockets` failed. Its immediate
cancellation could prevent the dispatched coroutine from entering `relay.run()`
at all. Patch 0007 uses `CoroutineStart.UNDISPATCHED` to establish the running
relay before cancellation, retaining the real sockets, deadline, and both
closure assertions. Production's separate pre-start ownership cleanup is already
covered by `VsockPortForwarderTest`; no relay runtime change was needed.

Existing compatibility-monitor PR [#100](https://github.com/0cwa/salvagenet-mvp/pull/100)
remains separate. Its recorded canaries stop at patch conflicts and its normal
source check detects uncaptured patch drift; those runs are not adoption evidence.

## Outcome and remaining qualification

Source reconstruction and runtime-input verification pass. Rebuilt software
verification is recorded by the PR's exact-head checks. The configured physical
sequence still needs `hil-smoke`, then relevant MVP/lifecycle coverage of the
new candidate. No physical gate, unattended-reliability claim, product phase,
or public release status is advanced by this sync.

An APK upgrade preserves operator-managed guest images. Before Alpine
qualification, stop the managed VM (or deliberately reset/re-provision the alpha
node), publish the verified v1.3.0 APK's kernel, initramfs, and rootfs with the
existing `upload-image <artifact_id> <file> --sha256 <digest>` CLI, and record
their sizes and digests. Use `podroid-kernel`, `podroid-initramfs`, and
`podroid-alpine-squashfs`, matching the runtime lock. `hil-smoke` installs with
`adb install -r` and does not replace those inputs; an APK-only update cannot
establish that an existing managed guest runs the new kernel/rootfs.
