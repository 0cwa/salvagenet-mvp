package org.nodehost.qemu

data class QemuLaunchDescriptor(
    val executable: String,
    val launcher: String?,
    val workingDirectory: String,
    val environment: Map<String, String>,
    val arguments: List<String>,
) {
    fun argv(): List<String> = listOfNotNull(launcher, executable) + arguments
}

enum class QemuBootMode { DIRECT_KERNEL, UEFI }

enum class QemuDiskLayout {
    /** Podroid invariant: writable ext4 state is vda and read-only SquashFS is vdb. */
    LEGACY_PODROID,

    /** Generic cloud-image invariant: system is vda and optional persistent data is vdb. */
    SYSTEM_THEN_DATA,
}

data class ResolvedVmLaunch(
    val instanceId: String,
    val qemuExecutable: String,
    val launcherExecutable: String?,
    val nativeLibraryDir: String,
    val workingDirectory: String,
    val bootMode: QemuBootMode,
    val diskLayout: QemuDiskLayout,
    val memoryMiB: Int,
    val vcpus: Int,
    val kernelPath: String? = null,
    val initramfsPath: String? = null,
    val kernelArguments: List<String> = emptyList(),
    val firmwareCodePath: String? = null,
    val firmwareVarsPath: String? = null,
    val metadataSeedUrl: String? = null,
    val systemDiskPath: String,
    val systemDiskFormat: String,
    val dataDiskPath: String?,
    val qmpSocketPath: String,
    val serialSocketPath: String,
    val consoleSocketPath: String,
    val recoverySshHostPort: Int,
)
