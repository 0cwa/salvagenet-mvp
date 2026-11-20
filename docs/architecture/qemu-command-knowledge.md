# QEMU command knowledge preservation

The product removes raw QEMU and kernel argument *settings*, not the knowledge Podroid accumulated.

## Preserved upstream constraints

The extraction task must snapshot the imported Podroid command before changing it. At minimum preserve and test:

- executable from `applicationInfo.nativeLibraryDir`;
- optional launcher preceding QEMU in argv;
- working directory in app-private files;
- `LD_LIBRARY_PATH` including native library and app files directories;
- dedicated long-lived spawn/reap thread because launcher parent-death behavior is thread-sensitive;
- ARM `virt` machine and GIC choice;
- TCG multi-thread mode and translation-block sizing policy;
- CPU model and performance flags;
- direct kernel/initramfs command-line assembly;
- separate writable and read-only block devices and I/O threads;
- SLIRP netdev and typed port-forward generation;
- serial, virtio-console, control, host-bridge, and QMP Unix sockets;
- headless display;
- USB controller only when explicitly enabled;
- stdout disposal, stderr draining, exit-code capture, and stale socket cleanup;
- 16 KiB native alignment checks.

## Typed compiler

`QemuCommandCompiler` consumes a validated `ResolvedVmLaunch` and emits argv plus an environment descriptor.

```text
VmProfile + RuntimeSpec + AllocatedPaths + ApprovedDebugOverrides
                          |
                          v
                 QemuCommandCompiler
                          |
                          v
               QemuLaunchDescriptor
```

No API or imported config can submit raw argv. A debug build may load a checked-in `QemuDebugOverride` fixture for upstream behavior reproduction. The release variant must exclude that source set.

## Golden tests

- `tests/qemu/podroid-upstream.argv` — static expansion of the pinned upstream command; only device-specific paths and Android IPv4 are substituted.
- `tests/qemu/podroid-baseline.argv` — exact production direct-kernel command, with instance-scoped paths and one loopback recovery SSH forward.
- `tests/qemu/podroid-baseline.metadata.json` — exact upstream commit/tree, capture inputs, and the explicit differences between those fixtures. This is source evidence, not a device execution capture.
- profile-specific golden argv files;
- invariant tests for loopback management forwards, path scoping, disk order, and socket uniqueness;
- parser tests proving spaces/quoting never come from naive string splitting.

## Podroid v1.3.0 adaptation

The source baseline is [Podroid v1.3.0 at `d5f7210182db9fbbee3ce6780ddd4b3e520e304b`](https://github.com/ExTV/Podroid/tree/d5f7210182db9fbbee3ce6780ddd4b3e520e304b),
with QEMU 11.1.2 and Linux 7.3. Its [QEMU command builder](https://github.com/ExTV/Podroid/blob/d5f7210182db9fbbee3ce6780ddd4b3e520e304b/app/src/main/java/com/excp/podroid/engine/QemuEngine.kt)
adds `arm64.nompam` to the direct-kernel command. The upstream [MPAM workaround](https://github.com/ExTV/Podroid/commit/d7c389b9bf706413aa9ffc61dc2e8adbe2bdfaa6)
addresses a guest kernel panic when advertised CPU capabilities are not usable.
The typed Podroid kernel profile retains that argument. Generic UEFI profiles
receive no kernel command line and keep their existing golden command.

Upstream can also pass Android DNS resolvers through `podroid.dns=`. The fixture
sets `dnsServers` to an empty list, and the typed SalvageNet path keeps its existing
network configuration without adding resolver discovery or a DNS adapter. This
update does not qualify Android-specific DNS behavior; that needs an explicit
networking change and device evidence.

Upstream now applies ordinary user port forwards over QMP after startup, keeping
only its implicit forwards on the launch command. SalvageNet retains its single
loopback recovery SSH forward; the upstream SSH, VNC, and audio forwards remain
documented only in the upstream fixture. The fixture comparison permits only the
documented path and forward changes between upstream and production snapshots.

## Adaptation points

Revisit an argument only after a measured boot, compatibility, thermal, or storage result. Record the change in an ADR or experiment result rather than deleting the old rationale.
