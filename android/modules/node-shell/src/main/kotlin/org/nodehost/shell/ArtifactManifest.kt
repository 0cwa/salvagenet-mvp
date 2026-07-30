package org.nodehost.shell

import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import org.json.JSONObject

/** The single versioned contract shared by artifact publication, listing, and runtime consumption. */
internal data class ArtifactManifest(
    val artifactId: String,
    val sha256: String,
    val sizeBytes: Long,
    val relativePath: String = expectedRelativePath(artifactId, sha256),
) {
    init {
        require(ARTIFACT_ID.matches(artifactId)) { "invalid artifact id" }
        require(SHA256.matches(sha256)) { "invalid artifact digest" }
        require(sizeBytes in 1..MAX_ARTIFACT_BYTES) { "artifact size is out of bounds" }
        require(relativePath == expectedRelativePath(artifactId, sha256)) { "artifact relative path is inconsistent" }
    }

    companion object {
        val ARTIFACT_ID = Regex("[a-z0-9][a-z0-9.-]{0,127}")
        val SHA256 = Regex("[a-f0-9]{64}")
        const val VERSION = 1
        const val MAX_MANIFEST_BYTES = 4096L
        const val MAX_ARTIFACT_BYTES = 64L * 1024 * 1024 * 1024
        val FIELDS = setOf("version", "sha256", "sizeBytes", "relativePath")

        fun expectedRelativePath(artifactId: String, digest: String) =
            "versions/$artifactId/$digest/payload"
    }
}

/** Fail-closed file adapter for active artifact manifests and digest-addressed payloads. */
internal class ArtifactManifestStore(private val root: File) {
    private val canonicalRoot by lazy { root.canonicalFile }

    fun active(artifactId: String): ArtifactManifest? {
        require(ArtifactManifest.ARTIFACT_ID.matches(artifactId)) { "invalid artifact id" }
        val file = manifestFile(artifactId)
        if (!file.exists()) return null
        check(file.isFile && file.length() in 1..ArtifactManifest.MAX_MANIFEST_BYTES) {
            "artifact manifest is out of bounds: $artifactId"
        }
        return try {
            val value = JSONObject(file.readText())
            check(value.keys().asSequence().toSet() == ArtifactManifest.FIELDS) {
                "artifact manifest fields are invalid: $artifactId"
            }
            check(value.getInt("version") == ArtifactManifest.VERSION) {
                "artifact manifest version is unsupported: $artifactId"
            }
            ArtifactManifest(
                artifactId = artifactId,
                sha256 = value.getString("sha256"),
                sizeBytes = value.getLong("sizeBytes"),
                relativePath = value.getString("relativePath"),
            ).also(::requirePayload)
        } catch (failure: Throwable) {
            if (failure is IllegalStateException && failure.message?.startsWith("artifact manifest") == true) throw failure
            throw IllegalStateException("artifact manifest is invalid: $artifactId", failure)
        }
    }

    fun listActive(limit: Int = 128): List<ArtifactManifest> {
        require(limit in 1..512)
        if (!root.exists()) return emptyList()
        check(root.isDirectory) { "artifact root is not a directory" }
        val artifactIds = root.listFiles()
            ?.filter { it.isFile && it.name.endsWith(MANIFEST_SUFFIX) }
            ?.map { it.name.removeSuffix(MANIFEST_SUFFIX) }
            ?.filter(ArtifactManifest.ARTIFACT_ID::matches)
            ?.sorted()
            .orEmpty()
        // This is an invariant bound, not pagination: silently omitting valid active artifacts would be dishonest.
        check(artifactIds.size <= limit) { "active artifact manifest count exceeded bound" }
        // A manifest may disappear after listFiles(); malformed valid manifests still fail closed as corruption.
        return artifactIds.mapNotNull(::active)
    }

    fun isPublished(artifactId: String, digest: String, sizeBytes: Long, verifyDigest: Boolean): Boolean {
        val manifest = try { active(artifactId) } catch (_: IllegalStateException) { return false } ?: return false
        if (manifest.sha256 != digest || manifest.sizeBytes != sizeBytes) return false
        return !verifyDigest || sha256(payload(manifest)) == digest
    }

    fun writeActive(manifest: ArtifactManifest, temporaryTag: String) {
        require(TEMPORARY_TAG.matches(temporaryTag)) { "invalid manifest temporary tag" }
        check(root.mkdirs() || root.isDirectory) { "artifact root is unavailable" }
        requirePayload(manifest)
        val target = manifestFile(manifest.artifactId)
        val temporary = File(root, ".${manifest.artifactId}.$temporaryTag.manifest.part")
        val value = JSONObject()
            .put("version", ArtifactManifest.VERSION)
            .put("sha256", manifest.sha256)
            .put("sizeBytes", manifest.sizeBytes)
            .put("relativePath", manifest.relativePath)
        try {
            FileOutputStream(temporary).use { output ->
                output.write(value.toString().toByteArray())
                output.fd.sync()
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

    fun versionPayload(artifactId: String, digest: String): File =
        resolveRelative(ArtifactManifest.expectedRelativePath(artifactId, digest))

    fun payload(manifest: ArtifactManifest): File = resolveRelative(manifest.relativePath)

    fun isActivePayload(artifactId: String, digest: String, relativePath: String): Boolean {
        val manifest = active(artifactId) ?: return false
        return manifest.sha256 == digest && manifest.relativePath == relativePath
    }

    private fun requirePayload(manifest: ArtifactManifest) {
        val payload = payload(manifest)
        check(payload.isFile && payload.length() == manifest.sizeBytes) {
            "artifact payload is missing or has the wrong size: ${manifest.artifactId}"
        }
    }

    private fun manifestFile(artifactId: String) = File(root, "$artifactId$MANIFEST_SUFFIX")

    private fun resolveRelative(relativePath: String): File {
        val resolved = File(canonicalRoot, relativePath).canonicalFile
        check(resolved.path.startsWith(canonicalRoot.path + File.separator)) { "artifact path escaped its root" }
        return resolved
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private companion object {
        const val MANIFEST_SUFFIX = ".manifest.json"
        val TEMPORARY_TAG = Regex("[a-z0-9-]{1,32}")
    }
}
