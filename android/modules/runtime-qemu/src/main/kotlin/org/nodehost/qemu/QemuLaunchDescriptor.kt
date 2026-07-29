package org.nodehost.qemu

import java.io.File

/** Internal process contract. Raw argv never crosses the runtime-qemu boundary. */
internal data class QemuLaunchDescriptor(
    val executable: File,
    val launcher: File?,
    val workingDirectory: File,
    val environment: Map<String, String>,
    val arguments: List<String>,
    val sockets: List<File>,
) {
    fun argv(): List<String> = listOfNotNull(launcher?.path, executable.path) + arguments
}

internal enum class QemuBootMode { DIRECT_KERNEL, UEFI }
internal enum class QemuDiskLayout { LEGACY_PODROID, SYSTEM_THEN_DATA }

internal data class ResolvedVmLaunch(
    val instanceId: String,
    val qemuExecutable: File,
    val launcherExecutable: File?,
    val nativeLibraryDir: File,
    val workingDirectory: File,
    val bootMode: QemuBootMode,
    val diskLayout: QemuDiskLayout,
    val memoryMiB: Int,
    val vcpus: Int,
    val kernelPath: File? = null,
    val initramfsPath: File? = null,
    val kernelArguments: List<String> = emptyList(),
    val firmwareCodePath: File? = null,
    val firmwareVarsPath: File? = null,
    val metadataSeedUrl: String? = null,
    val systemDiskPath: File,
    val systemDiskFormat: String,
    val dataDiskPath: File?,
    val qmpSocketPath: File,
    val serialSocketPath: File,
    val consoleSocketPath: File,
    val controlSocketPath: File,
    val hostSocketPath: File,
    val recoverySshHostPort: Int,
)
