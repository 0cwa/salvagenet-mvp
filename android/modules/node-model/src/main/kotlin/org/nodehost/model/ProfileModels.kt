package org.nodehost.model

private val artifactIdPattern = Regex("[a-z0-9][a-z0-9.-]{0,127}")
private val sha256Pattern = Regex("[a-f0-9]{64}")
private val checkedInAssetPattern = Regex("guest-init/[a-z0-9./_-]+")

enum class Architecture { AARCH64 }
enum class MachineFamily { VIRT }
enum class Acceleration { TCG }
enum class DeviceTransport { PCI }
enum class BootKind { DIRECT_KERNEL, UEFI }
enum class InitializationKind { LEGACY_PODROID, NOCLOUD_NET }
enum class DiskFormat { RAW, QCOW2, SQUASHFS }
enum class WritableLayer { QCOW2_OVERLAY, SEPARATE_EXT4_OVERLAY, NONE }
enum class HealthKind { CONSOLE_MARKER, METADATA_CALLBACK, SSH }

data class ArtifactRef(
    val id: String,
    val sha256: String,
    val expectedSizeBytes: Long,
) {
    init {
        require(artifactIdPattern.matches(id)) { "invalid artifact id" }
        require(sha256Pattern.matches(sha256)) { "sha256 must be lowercase hexadecimal" }
        require(expectedSizeBytes > 0) { "expectedSizeBytes must be positive" }
    }
}

data class MachineSpec(
    val family: MachineFamily = MachineFamily.VIRT,
    val acceleration: Acceleration = Acceleration.TCG,
    val deviceTransport: DeviceTransport = DeviceTransport.PCI,
    val cpuModel: String? = null,
) {
    init { require(cpuModel == null || Regex("[a-z0-9_-]{1,32}").matches(cpuModel)) }
}

sealed interface BootSpec {
    val kind: BootKind

    data class DirectKernel(
        val kernel: ArtifactRef,
        val initramfs: ArtifactRef,
        val kernelArgumentProfile: String,
    ) : BootSpec {
        override val kind = BootKind.DIRECT_KERNEL
        init { require(Regex("[a-z0-9][a-z0-9-]{0,63}").matches(kernelArgumentProfile)) }
    }

    data class Uefi(val firmwareCode: ArtifactRef, val firmwareVars: ArtifactRef) : BootSpec {
        override val kind = BootKind.UEFI
    }
}

data class SystemDiskSpec(
    val artifact: ArtifactRef,
    val format: DiskFormat,
    val writableLayer: WritableLayer,
)

data class DataDiskSpec(
    val defaultSizeGiB: Int,
    val persistent: Boolean,
) {
    init { require(defaultSizeGiB in 1..1024) }
}

data class InitializationSpec(
    val kind: InitializationKind,
    val vendorDataAsset: String? = null,
    val metadataPath: String? = null,
) {
    init {
        require(vendorDataAsset == null || checkedInAssetPattern.matches(vendorDataAsset)) {
            "vendor data must reference a checked-in guest-init asset"
        }
        when (kind) {
            InitializationKind.LEGACY_PODROID -> require(metadataPath == null)
            InitializationKind.NOCLOUD_NET -> require(metadataPath?.startsWith("/v1/bootstrap/") == true)
        }
    }
}

data class RecoverySshSpec(val guestPort: Int = 22, val loopbackOnly: Boolean = true) {
    init {
        require(guestPort == 22) { "recovery SSH guest port is fixed" }
        require(loopbackOnly) { "recovery SSH must bind loopback" }
    }
}

data class HealthSpec(val kind: HealthKind, val marker: String? = null) {
    init {
        require(marker == null || marker.length in 1..128)
        require(kind == HealthKind.CONSOLE_MARKER || marker == null)
    }
}

data class ProfileRequirements(
    val minimumMemoryMiB: Int,
    val minimumStorageGiB: Int,
    val qualificationChecks: Set<String> = emptySet(),
) {
    init {
        require(minimumMemoryMiB in 256..16384)
        require(minimumStorageGiB in 1..1024)
        require(qualificationChecks.size <= 32)
        require(qualificationChecks.all { Regex("[a-z0-9][a-z0-9-]{0,63}").matches(it) })
    }
}

data class VmProfile(
    val id: VmProfileId,
    val version: Int,
    val extends: VmProfileId? = null,
    val architecture: Architecture = Architecture.AARCH64,
    val machine: MachineSpec,
    val boot: BootSpec,
    val systemDisk: SystemDiskSpec,
    val dataDisk: DataDiskSpec? = null,
    val initialization: InitializationSpec,
    val recoverySsh: RecoverySshSpec,
    val health: HealthSpec,
    val requirements: ProfileRequirements,
) {
    init { require(version >= 1) }
}
