package org.nodehost.model

enum class BootKind { DIRECT_KERNEL, UEFI }
enum class InitializationKind { LEGACY_PODROID, NOCLOUD_NET }
enum class DiskFormat { RAW, QCOW2, SQUASHFS }

data class ArtifactRef(val id: String, val sha256: String?, val expectedSizeBytes: Long?)

data class VmProfile(
    val id: VmProfileId,
    val version: Int,
    val architecture: String,
    val bootKind: BootKind,
    val initializationKind: InitializationKind,
    val systemArtifact: ArtifactRef,
    val kernelArtifact: ArtifactRef? = null,
    val initramfsArtifact: ArtifactRef? = null,
    val firmwareCodeArtifact: ArtifactRef? = null,
    val firmwareVarsArtifact: ArtifactRef? = null,
    val minimumMemoryMiB: Int,
    val minimumStorageGiB: Int,
    val qualificationChecks: List<String> = emptyList(),
)
