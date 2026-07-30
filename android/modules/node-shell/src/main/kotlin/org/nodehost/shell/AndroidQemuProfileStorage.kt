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
        profiles.profile(id, verifyArtifacts, ::artifact)

    internal fun profileSummaries(): List<PackagedProfileSummary> = profiles.summaries()

    internal fun vendorData(id: VmProfileId): ByteArray = profiles.vendorData(id)

    internal fun prepareDisks(runtime: RuntimeSpec) {
        val profile = profile(runtime.profileId, verifyArtifacts = true)
        val instance = instanceDirectory().apply { check(mkdirs() || isDirectory) }
        val artifacts = File(instance, "artifacts").apply { check(mkdirs() || isDirectory) }
        when (val boot = profile.boot) {
            is BootSpec.DirectKernel -> {
                copyVerified(boot.kernel.id, File(artifacts, "vmlinuz-virt"))
                copyVerified(boot.initramfs.id, File(artifacts, "initrd.img"))
                copyVerified(profile.systemDisk.artifact.id, File(artifacts, "alpine-rootfs.squashfs"))
                val overlay = File(instance, "storage.img")
                if (!overlay.exists()) RandomAccessFile(overlay, "rw").use { it.setLength(runtime.dataDiskGiB * GIB) }
            }
            is BootSpec.Uefi -> {
                copyVerified(boot.firmwareCode.id, File(artifacts, "AAVMF_CODE.fd"))
                // These are mutable VM state. Verify the imported source, but create each target exactly once.
                copyVerifiedOnce(boot.firmwareVars.id, File(instance, "firmware-vars.fd"))
                copyVerifiedOnce(profile.systemDisk.artifact.id, File(instance, "system.qcow2"))
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

    private fun artifact(id: String, verify: Boolean): ArtifactRef {
        val manifest = manifests.active(id)
        if (manifest != null) {
            val file = manifests.payload(manifest)
            if (verify) require(sha256(file) == manifest.sha256) { "artifact digest mismatch: $id" }
            return ArtifactRef(id, manifest.sha256, manifest.sizeBytes)
        }
        require(id in LEGACY_PODROID_ARTIFACT_IDS) {
            "active artifact manifest is required: $id"
        }
        val file = File(artifactRoot, id)
        require(file.isFile && file.length() in 1..MAX_ARTIFACT_BYTES) { "trusted artifact is missing or out of bounds: $id" }
        val digest = sha256(file)
        if (verify) require(expectedLegacyDigest(id) == digest) { "artifact digest mismatch: $id" }
        return ArtifactRef(id, digest, file.length())
    }

    private fun artifactFile(id: String): File {
        val manifest = manifests.active(id)
        if (manifest != null) return manifests.payload(manifest)
        require(id in LEGACY_PODROID_ARTIFACT_IDS) {
            "active artifact manifest is required: $id"
        }
        return File(artifactRoot, id)
    }

    private fun expectedLegacyDigest(id: String): String {
        require(id in LEGACY_PODROID_ARTIFACT_IDS) { "legacy digest metadata is not allowed for artifact: $id" }
        val expected = File(artifactRoot, "$id.sha256")
        require(expected.isFile && expected.length() <= 128) { "artifact digest metadata is missing: $id" }
        return expected.readText().trim()
    }

    private fun copyVerifiedOnce(id: String, target: File) {
        artifact(id, true)
        if (target.exists()) {
            require(target.isFile && target.length() in 1..MAX_ARTIFACT_BYTES) { "mutable system state is invalid: ${target.name}" }
            return
        }
        copyVerified(id, target)
    }

    private fun copyVerified(id: String, target: File) {
        val source = artifactFile(id)
        artifact(id, true)
        if (target.isFile && target.length() == source.length() && sha256(target) == sha256(source)) return
        val temporary = File(target.parentFile, target.name + ".tmp")
        FileInputStream(source).use { input ->
            FileOutputStream(temporary).use { output ->
                input.copyTo(output)
                output.fd.sync()
            }
        }
        check(temporary.renameTo(target)) { "atomic artifact publication failed: $id" }
    }

    private fun sha256(file: File): String {
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
