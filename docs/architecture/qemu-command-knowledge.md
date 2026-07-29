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

- `tests/qemu/podroid-baseline.argv` — exact imported baseline after normalization.
- profile-specific golden argv files;
- invariant tests for loopback management forwards, path scoping, disk order, and socket uniqueness;
- parser tests proving spaces/quoting never come from naive string splitting.

## Adaptation points

Revisit an argument only after a measured boot, compatibility, thermal, or storage result. Record the change in an ADR or experiment result rather than deleting the old rationale.
