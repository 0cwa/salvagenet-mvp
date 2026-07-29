# runtime-qemu

Podroid-derived QEMU runtime adapter.

Production callers provide only `VmProfile`, `RuntimeSpec`, and `QemuRuntimeAllocation` to `QemuProfileResolver`, then pass the opaque `QemuLaunchPlan` to `QemuRuntimeAdapter`. Raw QEMU argv, kernel arguments, and QMP are module-internal.

The adapter preserves the APK-native `nativeLibraryDir/libpodroid-launcher.so -> libqemu-system-aarch64.so` path. Spawn and blocking reap execute in one dedicated long-lived runnable because the launcher's parent-death behavior is thread-sensitive. Mutable files, artifacts, and Unix sockets are rooted at `files/vms/<instance-id>/`; recovery SSH binds loopback.

QMP supports only fixed internal lifecycle commands. Each operation has a deadline, bounded response size/event fan-in, and a per-session request cap. Process stderr is drained into a bounded diagnostic tail and stale sockets are removed before launch.
