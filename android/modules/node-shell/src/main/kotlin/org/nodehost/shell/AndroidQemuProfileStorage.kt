package org.nodehost.shell

import android.content.Context
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import org.nodehost.model.ArtifactRef
import org.nodehost.model.BootSpec
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfile
import org.nodehost.model.VmProfileId

internal const val ALPINE_PROFILE_ID = "alpine-direct-qualification"

/** Owns canonical profile resolution and offline disk/artifact effects; process lifecycle stays in AndroidQemuRuntimeBackend. */
internal class AndroidQemuProfileStorage(
    context: Context,
    private val atomicMove: (File, File) -> Unit = { source, target ->
        Files.move(source.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE)
    },
) {
    private val application = context.applicationContext
    private val artifactRoot = File(application.filesDir, "nodehost-artifacts")
    private val manifests = ArtifactManifestStore(artifactRoot)
    private val profiles = AndroidPackagedProfileCatalog(application)

    internal fun profile(id: VmProfileId, verifyArtifacts: Boolean): VmProfile =
        resolveProfile(id, verifyArtifacts).profile

    internal fun profileSummaries(): List<PackagedProfileSummary> = profiles.summaries()

    internal fun vendorData(id: VmProfileId): ByteArray = profiles.vendorData(id)

    internal fun prepareDisks(runtime: RuntimeSpec) {
        // Resolve and verify each source artifact once for this preparation, then reuse its typed identity and file.
        val resolved = resolveProfile(runtime.profileId, verifyArtifacts = true)
        val profile = resolved.profile
        val instance = instanceDirectory().apply { check(mkdirs() || isDirectory) }
        val artifacts = File(instance, "artifacts").apply { check(mkdirs() || isDirectory) }
        when (val boot = profile.boot) {
            is BootSpec.DirectKernel -> {
                copyVerified(resolved.artifact(boot.kernel.id), File(artifacts, "vmlinuz-virt"))
                copyVerified(resolved.artifact(boot.initramfs.id), File(artifacts, "initrd.img"))
                copyVerified(resolved.artifact(profile.systemDisk.artifact.id), File(artifacts, "alpine-rootfs.squashfs"))
                val overlay = File(instance, "storage.img")
                if (!overlay.exists()) RandomAccessFile(overlay, "rw").use { it.setLength(runtime.dataDiskGiB * GIB) }
            }
            is BootSpec.Uefi -> {
                copyVerified(resolved.artifact(boot.firmwareCode.id), File(artifacts, "AAVMF_CODE.fd"))
                // These are mutable VM state. Verify the imported source, but create each target exactly once.
                copyVerifiedOnce(resolved.artifact(boot.firmwareVars.id), File(instance, "firmware-vars.fd"))
                copyVerifiedOnce(resolved.artifact(profile.systemDisk.artifact.id), File(instance, "system.qcow2"))
                val data = File(instance, "data.raw")
                val durable = durableDataFile()
                if (!data.exists() && durable.exists()) {
                    atomicMove(durable, data)
                    check(data.isFile && !durable.exists()) { "data disk restoration was not atomic" }
                }
                if (!data.exists()) RandomAccessFile(data, "rw").use { it.setLength(runtime.dataDiskGiB * GIB) }
            }
        }
    }

    internal fun removeSystem(runtime: RuntimeSpec) {
        val instance = instanceDirectory()
        val data = File(instance, "data.raw")
        if (runtime.preserveDataOnDelete && data.exists()) {
            val durable = durableDataFile()
            check(durable.parentFile?.mkdirs() == true || durable.parentFile?.isDirectory == true) { "durable data directory unavailable" }
            check(!durable.exists()) { "durable data disk already exists" }
            atomicMove(data, durable)
            check(durable.isFile && !data.exists()) { "data disk preservation was not atomic" }
        }
        deleteBounded(instance, MAX_DELETE_ENTRIES)
    }

    internal fun instanceDirectory() = File(application.filesDir, "vms/default")

    private fun durableDataFile() = File(application.filesDir, "nodehost-durable/vms/default/data.raw")

    private fun resolveProfile(id: VmProfileId, verifyArtifacts: Boolean): ResolvedProfile {
        val artifacts = linkedMapOf<String, ResolvedArtifact>()
        val profile = profiles.profile(id, verifyArtifacts) { artifactId, verify ->
            artifacts.getOrPut(artifactId) { resolveArtifact(artifactId, verify) }.reference
        }
        return ResolvedProfile(profile, artifacts)
    }

    private fun resolveArtifact(id: String, verify: Boolean): ResolvedArtifact {
        val manifest = manifests.active(id)
        if (manifest != null) {
            val file = manifests.payload(manifest)
            if (verify) require(fileDigest(file) == manifest.sha256) { "artifact digest mismatch: $id" }
            return ResolvedArtifact(ArtifactRef(id, manifest.sha256, manifest.sizeBytes), file)
        }
        require(id in LEGACY_PODROID_ARTIFACT_IDS) {
            "active artifact manifest is required: $id"
        }
        val file = File(artifactRoot, id)
        require(file.isFile && file.length() in 1..MAX_ARTIFACT_BYTES) { "trusted artifact is missing or out of bounds: $id" }
        val expectedDigest = expectedLegacyPodroidDigest(id)
        if (verify) require(fileDigest(file) == expectedDigest) { "artifact digest mismatch: $id" }
        return ResolvedArtifact(ArtifactRef(id, expectedDigest, file.length()), file)
    }

    private fun expectedLegacyPodroidDigest(id: String): String {
        require(id in LEGACY_PODROID_ARTIFACT_IDS) { "legacy digest metadata is not allowed for artifact: $id" }
        val expected = File(artifactRoot, "$id.sha256")
        require(expected.isFile && expected.length() <= 128) { "artifact digest metadata is missing: $id" }
        return expected.readText().trim().also {
            require(ArtifactManifest.SHA256.matches(it)) { "artifact digest metadata is invalid: $id" }
        }
    }

    private fun copyVerifiedOnce(artifact: ResolvedArtifact, target: File) {
        if (target.exists()) {
            require(target.isFile && target.length() in 1..MAX_ARTIFACT_BYTES) { "mutable system state is invalid: ${target.name}" }
            return
        }
        copyVerified(artifact, target)
    }

    private fun copyVerified(artifact: ResolvedArtifact, target: File) {
        if (
            target.isFile &&
            target.length() == artifact.reference.expectedSizeBytes &&
            fileDigest(target) == artifact.reference.sha256
        ) return

        val temporary = File(target.parentFile, target.name + ".tmp")
        try {
            val copiedDigest = MessageDigest.getInstance("SHA-256")
            FileInputStream(artifact.file).use { input ->
                FileOutputStream(temporary).use { output ->
                    val buffer = ByteArray(COPY_BUFFER_BYTES)
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        copiedDigest.update(buffer, 0, count)
                        output.write(buffer, 0, count)
                    }
                    output.fd.sync()
                }
            }
            val actualDigest = copiedDigest.digest().joinToString("") { "%02x".format(it) }
            check(temporary.length() == artifact.reference.expectedSizeBytes) {
                "copied artifact has the wrong size: ${artifact.reference.id}"
            }
            check(actualDigest == artifact.reference.sha256) {
                "copied artifact digest mismatch: ${artifact.reference.id}"
            }
            Files.move(
                temporary.toPath(),
                target.toPath(),
                StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING,
            )
        } finally {
            temporary.delete()
        }
    }

    private fun fileDigest(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(COPY_BUFFER_BYTES)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun deleteBounded(root: File, remaining: Int): Int {
        if (!root.exists()) return remaining
        require(remaining > 0) { "runtime deletion exceeded entry bound" }
        var budget = remaining - 1
        root.listFiles()?.forEach { budget = deleteBounded(it, budget) }
        check(root.delete()) { "failed to delete runtime path" }
        return budget
    }

    private data class ResolvedArtifact(
        val reference: ArtifactRef,
        val file: File,
    )

    private data class ResolvedProfile(
        val profile: VmProfile,
        val artifacts: Map<String, ResolvedArtifact>,
    ) {
        fun artifact(id: String): ResolvedArtifact = checkNotNull(artifacts[id]) {
            "resolved profile is missing artifact: $id"
        }
    }

    private companion object {
        val LEGACY_PODROID_ARTIFACT_IDS = setOf(
            "podroid-kernel",
            "podroid-initramfs",
            "podroid-alpine-squashfs",
        )
        const val COPY_BUFFER_BYTES = 1024 * 1024
        const val MAX_ARTIFACT_BYTES = ArtifactManifest.MAX_ARTIFACT_BYTES
        const val MAX_DELETE_ENTRIES = 4096
        const val GIB = 1024L * 1024 * 1024
    }
}
