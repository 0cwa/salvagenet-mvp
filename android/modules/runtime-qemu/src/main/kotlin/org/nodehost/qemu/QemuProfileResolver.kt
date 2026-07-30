package org.nodehost.qemu

import android.content.Context
import java.io.File
import org.nodehost.model.BootSpec
import org.nodehost.model.DiskFormat
import org.nodehost.model.InitializationKind
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfile
import org.nodehost.model.WritableLayer

@JvmInline
value class RecoverySshHostPort(val value: Int) {
    init { require(value in 1024..65_535) { "invalid recovery SSH port" } }
}

@JvmInline
value class BootstrapToken(val value: String) {
    init { require(Regex("[A-Za-z0-9_-]{16,128}").matches(value)) { "invalid bootstrap token" } }
}

/** Android-owned directories and bounded allocations; no caller-supplied argv or kernel command line. */
class QemuRuntimeAllocation internal constructor(
    internal val nativeLibraryDir: File,
    internal val filesDirectory: File,
    internal val recoverySshHostPort: RecoverySshHostPort,
    internal val bootstrapToken: BootstrapToken? = null,
) {
    init { require(nativeLibraryDir.isAbsolute && filesDirectory.isAbsolute) { "runtime directories must be absolute" } }

    companion object {
        fun fromApplication(
            context: Context,
            recoverySshHostPort: RecoverySshHostPort,
            bootstrapToken: BootstrapToken? = null,
        ) = QemuRuntimeAllocation(
            File(context.applicationInfo.nativeLibraryDir), context.filesDir,
            recoverySshHostPort, bootstrapToken,
        )
    }
}

/** Opaque typed plan: production callers cannot inspect or alter QEMU/QMP command surfaces. */
class QemuLaunchPlan internal constructor(internal val resolved: ResolvedVmLaunch)

/** Resolves authoritative profile/runtime models to one instance-scoped launch plan. */
class QemuProfileResolver {
    fun resolve(
        profile: VmProfile,
        runtime: RuntimeSpec,
        allocation: QemuRuntimeAllocation,
    ): QemuLaunchPlan {
        val resolved = resolveInternal(profile, runtime, allocation)
        return QemuLaunchPlan(resolved)
    }

    private fun resolveInternal(
        profile: VmProfile,
        runtime: RuntimeSpec,
        allocation: QemuRuntimeAllocation,
    ): ResolvedVmLaunch {
        require(runtime.id.value == "default") { "MVP supports one runtime" }
        require(runtime.profileId == profile.id) { "runtime profile does not match resolved profile" }
        require(runtime.memoryMiB >= profile.requirements.minimumMemoryMiB) { "profile memory minimum not met" }
        require(runtime.dataDiskGiB >= profile.requirements.minimumStorageGiB) { "profile storage minimum not met" }
        require(profile.machine.cpuModel == null || profile.machine.cpuModel == "max") { "unsupported CPU model" }

        val filesRoot = allocation.filesDirectory.canonicalFile
        val nativeRoot = allocation.nativeLibraryDir.canonicalFile
        val instance = child(filesRoot, "vms/${runtime.id.value}")
        val artifacts = child(instance, "artifacts")
        val qemu = child(nativeRoot, "libqemu-system-aarch64.so")
        val launcher = child(nativeRoot, "libpodroid-launcher.so")
        val boot = profile.boot

        val direct = boot as? BootSpec.DirectKernel
        val uefi = boot as? BootSpec.Uefi
        val legacy = profile.initialization.kind == InitializationKind.LEGACY_PODROID
        require(legacy == (direct != null)) { "direct-kernel and legacy initialization must be paired" }
        if (direct != null) {
            require(direct.kernelArgumentProfile == PODROID_KERNEL_ARGUMENT_PROFILE) {
                "unsupported kernel argument profile"
            }
            require(profile.systemDisk.writableLayer == WritableLayer.SEPARATE_EXT4_OVERLAY)
            require(profile.systemDisk.format == DiskFormat.SQUASHFS && profile.dataDisk != null)
        } else {
            require(uefi != null && profile.systemDisk.writableLayer == WritableLayer.COPIED_WRITABLE)
            require(profile.systemDisk.format == DiskFormat.QCOW2)
        }

        val metadataUrl = if (profile.initialization.kind == InitializationKind.NOCLOUD_NET) {
            val token = requireNotNull(allocation.bootstrapToken) { "NoCloud profile requires bootstrap token" }
            val path = requireNotNull(profile.initialization.metadataPath).replace("{token}", token.value)
            require(!path.contains('{') && path.startsWith("/v1/bootstrap/") && path.endsWith('/'))
            "http://10.0.2.2:8080$path"
        } else null

        return ResolvedVmLaunch(
            instanceId = runtime.id.value,
            qemuExecutable = qemu,
            launcherExecutable = launcher,
            nativeLibraryDir = nativeRoot,
            workingDirectory = instance,
            bootMode = if (direct != null) QemuBootMode.DIRECT_KERNEL else QemuBootMode.UEFI,
            diskLayout = if (legacy) QemuDiskLayout.LEGACY_PODROID else QemuDiskLayout.SYSTEM_THEN_DATA,
            memoryMiB = runtime.memoryMiB,
            vcpus = runtime.vcpus,
            kernelPath = direct?.let { child(artifacts, artifactFileName(it.kernel.id)) },
            initramfsPath = direct?.let { child(artifacts, artifactFileName(it.initramfs.id)) },
            kernelArguments = if (direct != null) podroidKernelArguments() else emptyList(),
            firmwareCodePath = uefi?.let { child(artifacts, artifactFileName(it.firmwareCode.id)) },
            firmwareVarsPath = uefi?.let { child(instance, "firmware-vars.fd") },
            metadataSeedUrl = metadataUrl,
            systemDiskPath = if (legacy) child(artifacts, artifactFileName(profile.systemDisk.artifact.id)) else child(instance, "system.${profile.systemDisk.format.extension}"),
            systemDiskFormat = profile.systemDisk.format.qemuFormat,
            dataDiskPath = profile.dataDisk?.let { child(instance, if (legacy) "storage.img" else "data.raw") },
            qmpSocketPath = child(instance, "qmp.sock"),
            serialSocketPath = child(instance, "serial.sock"),
            consoleSocketPath = child(instance, "terminal.sock"),
            controlSocketPath = child(instance, "ctrl.sock"),
            hostSocketPath = child(instance, "host.sock"),
            recoverySshHostPort = allocation.recoverySshHostPort.value,
        ).also(::validateResolvedPaths)
    }

    private fun validateResolvedPaths(launch: ResolvedVmLaunch) {
        val instanceRoot = launch.workingDirectory.canonicalFile
        val scoped = listOfNotNull(
            launch.kernelPath, launch.initramfsPath, launch.firmwareCodePath, launch.firmwareVarsPath,
            launch.systemDiskPath, launch.dataDiskPath, launch.qmpSocketPath, launch.serialSocketPath,
            launch.consoleSocketPath, launch.controlSocketPath, launch.hostSocketPath,
        )
        require(scoped.all { it.canonicalFile.isWithin(instanceRoot) }) { "launch path escaped instance directory" }
        require(requireNotNull(launch.qemuExecutable.parentFile).canonicalFile == launch.nativeLibraryDir)
        launch.launcherExecutable?.let {
            require(requireNotNull(it.parentFile).canonicalFile == launch.nativeLibraryDir)
        }
    }

    private fun child(parent: File, relative: String): File {
        require(relative.isNotBlank() && !File(relative).isAbsolute && relative.split('/').none { it == ".." })
        return File(parent, relative).canonicalFile.also { require(it.isWithin(parent.canonicalFile)) }
    }

    private fun artifactFileName(id: String): String = when (id) {
        "podroid-kernel" -> "vmlinuz-virt"
        "podroid-initramfs" -> "initrd.img"
        "podroid-alpine-squashfs" -> "alpine-rootfs.squashfs"
        "aavmf-code" -> "AAVMF_CODE.fd"
        else -> id
    }

    private fun podroidKernelArguments() = listOf(
        "console=ttyAMA0", "mitigations=off", "loglevel=1", "quiet", "mitigations=off",
        "androidip=10.0.2.2", "ssh=1", "podroid.x11.dpi=96",
    )

    private fun File.isWithin(root: File): Boolean = path == root.path || path.startsWith(root.path + File.separator)

    private val DiskFormat.extension: String get() = when (this) {
        DiskFormat.RAW -> "raw"
        DiskFormat.QCOW2 -> "qcow2"
        DiskFormat.SQUASHFS -> "squashfs"
    }
    private val DiskFormat.qemuFormat: String get() = if (this == DiskFormat.QCOW2) "qcow2" else "raw"

    private companion object {
        const val PODROID_KERNEL_ARGUMENT_PROFILE = "podroid-compatible-v1"
    }
}
