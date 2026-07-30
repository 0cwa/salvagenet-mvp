package org.nodehost.shell

import android.content.Context
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.security.SecureRandom
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.nodehost.api.ArtifactUploadCreateRequest
import org.nodehost.api.ArtifactUploadState
import org.nodehost.api.ArtifactUploadUseCases
import org.nodehost.api.HostArtifactUpload
import org.nodehost.api.HostCapability
import org.nodehost.api.HostDiagnostics
import org.nodehost.api.HostImage
import org.nodehost.api.HostProfile
import org.nodehost.api.HostResourceQueries
import org.nodehost.api.HostStatus
import org.nodehost.api.HostVm
import org.nodehost.model.OperationRecord
import org.nodehost.model.RuntimeId

/** File-backed, resumable controller upload adapter. No live credential or remote URL is persisted. */
internal class AndroidArtifactUploadStore(
    context: Context,
    private val clockMillis: () -> Long = System::currentTimeMillis,
    private val idFactory: () -> String = ::secureUploadId,
) : ArtifactUploadUseCases {
    private val uploadsRoot = File(context.filesDir, "nodehost-uploads")
    private val artifactsRoot = File(context.filesDir, "nodehost-artifacts")
    private val lock = Mutex()

    override suspend fun createUpload(
        request: ArtifactUploadCreateRequest,
        idempotencyKey: String,
        canonicalRequest: ByteArray,
    ): HostArtifactUpload = withContext(Dispatchers.IO) {
        lock.withLock {
            validateKey(idempotencyKey)
            require(canonicalRequest.isNotEmpty() && canonicalRequest.size <= MAX_CANONICAL_BYTES) {
                "canonical upload request is out of bounds"
            }
            ensureRoots()
            collectStaleLocked()
            val digest = sha256(canonicalRequest)
            uploadDirectoriesLocked().asSequence().map(::loadAndRecoverLocked).firstOrNull {
                it.idempotencyKey == idempotencyKey
            }?.let { existing ->
                require(existing.requestDigest == digest) { "idempotency key reused with different upload request" }
                return@withLock existing.resource()
            }
            require(uploadDirectoriesLocked().size < MAX_UPLOADS) { "upload capacity exceeded" }
            if (!published(request.artifactId, request.sha256, request.expectedSizeBytes)) preflightLocked(request.expectedSizeBytes)
            val id = idFactory()
            require(UPLOAD_ID.matches(id)) { "upload id factory returned invalid id" }
            val directory = uploadDirectory(id)
            check(directory.mkdir()) { "upload directory could not be created" }
            val now = clockMillis()
            val metadata = UploadMetadata(
                id = id,
                artifactId = request.artifactId,
                sha256 = request.sha256,
                expectedSizeBytes = request.expectedSizeBytes,
                committedBytes = if (published(request.artifactId, request.sha256, request.expectedSizeBytes)) request.expectedSizeBytes else 0,
                state = if (published(request.artifactId, request.sha256, request.expectedSizeBytes)) ArtifactUploadState.COMPLETED else ArtifactUploadState.OPEN,
                idempotencyKey = idempotencyKey,
                requestDigest = digest,
                createdAtEpochMs = now,
                updatedAtEpochMs = now,
            )
            writeMetadataLocked(metadata)
            metadata.resource()
        }
    }

    override suspend fun upload(id: String): HostArtifactUpload? = withContext(Dispatchers.IO) {
        lock.withLock {
            validateUploadId(id)
            val directory = uploadDirectory(id)
            if (!directory.isDirectory) null else loadAndRecoverLocked(directory).resource()
        }
    }

    override suspend fun writeChunk(
        id: String,
        offset: Long,
        chunkSha256: String,
        bytes: ByteArray,
    ): HostArtifactUpload = withContext(Dispatchers.IO) {
        require(bytes.size in 1..MAX_CHUNK_BYTES) { "upload chunk size is out of range" }
        require(SHA256.matches(chunkSha256) && sha256(bytes) == chunkSha256) { "upload chunk digest mismatch" }
        lock.withLock {
            validateUploadId(id)
            var metadata = requireMetadataLocked(id)
            require(metadata.state == ArtifactUploadState.OPEN) { "upload is not open" }
            val payload = payloadFile(id)
            reconcilePayloadLocked(metadata, payload)
            require(offset >= 0) { "upload offset must be non-negative" }
            if (offset < metadata.committedBytes) {
                require(offset + bytes.size <= metadata.committedBytes) { "upload chunk partially overlaps committed data" }
                val existing = ByteArray(bytes.size)
                RandomAccessFile(payload, "r").use { file -> file.seek(offset); file.readFully(existing) }
                require(existing.contentEquals(bytes)) { "upload chunk conflicts with committed data" }
                return@withLock metadata.resource()
            }
            require(offset == metadata.committedBytes) { "upload chunks must be sequential" }
            require(metadata.committedBytes <= metadata.expectedSizeBytes - bytes.size) { "upload exceeds expected size" }
            RandomAccessFile(payload, "rw").use { file ->
                if (file.length() > metadata.committedBytes) file.setLength(metadata.committedBytes)
                require(file.length() == metadata.committedBytes) { "upload payload length is inconsistent" }
                file.seek(offset)
                file.write(bytes)
                file.fd.sync()
            }
            metadata = metadata.copy(
                committedBytes = metadata.committedBytes + bytes.size,
                updatedAtEpochMs = clockMillis(),
            )
            writeMetadataLocked(metadata)
            metadata.resource()
        }
    }

    override suspend fun completeUpload(id: String): HostImage = withContext(Dispatchers.IO) {
        lock.withLock {
            validateUploadId(id)
            var metadata = requireMetadataLocked(id)
            if (metadata.state == ArtifactUploadState.COMPLETED) {
                require(published(metadata.artifactId, metadata.sha256, metadata.expectedSizeBytes)) { "completed upload artifact is unavailable" }
                return@withLock metadata.image()
            }
            require(metadata.state == ArtifactUploadState.OPEN) { "upload is cancelled" }
            val payload = payloadFile(id)
            reconcilePayloadLocked(metadata, payload)
            require(metadata.committedBytes == metadata.expectedSizeBytes) { "upload is incomplete" }
            require(payload.isFile && payload.length() == metadata.expectedSizeBytes) { "upload payload size mismatch" }
            require(sha256(payload) == metadata.sha256) { "upload digest mismatch" }
            RandomAccessFile(payload, "rw").use { it.fd.sync() }
            publishLocked(metadata, payload)
            metadata = metadata.copy(state = ArtifactUploadState.COMPLETED, updatedAtEpochMs = clockMillis())
            writeMetadataLocked(metadata)
            metadata.image()
        }
    }

    override suspend fun cancelUpload(id: String): HostArtifactUpload = withContext(Dispatchers.IO) {
        lock.withLock {
            validateUploadId(id)
            var metadata = requireMetadataLocked(id)
            if (metadata.state != ArtifactUploadState.OPEN) return@withLock metadata.resource()
            val payload = payloadFile(id)
            if (payload.exists()) check(payload.delete()) { "upload staging payload could not be removed" }
            metadata = metadata.copy(state = ArtifactUploadState.CANCELLED, updatedAtEpochMs = clockMillis())
            writeMetadataLocked(metadata)
            metadata.resource()
        }
    }

    suspend fun recoverAndCollect() = withContext(Dispatchers.IO) {
        lock.withLock {
            ensureRoots()
            collectStaleLocked()
            uploadDirectoriesLocked().forEach(::loadAndRecoverLocked)
            cleanupInterruptedPublicationsLocked()
        }
    }

    private fun requireMetadataLocked(id: String): UploadMetadata {
        val directory = uploadDirectory(id)
        require(directory.isDirectory) { "upload not found" }
        return loadAndRecoverLocked(directory)
    }

    private fun loadAndRecoverLocked(directory: File): UploadMetadata {
        var metadata = readMetadataLocked(directory)
        if (metadata.state == ArtifactUploadState.OPEN && published(metadata.artifactId, metadata.sha256, metadata.expectedSizeBytes)) {
            payloadFile(metadata.id).delete()
            metadata = metadata.copy(
                committedBytes = metadata.expectedSizeBytes,
                state = ArtifactUploadState.COMPLETED,
                updatedAtEpochMs = clockMillis(),
            )
            writeMetadataLocked(metadata)
            return metadata
        }
        if (metadata.state == ArtifactUploadState.OPEN) reconcilePayloadLocked(metadata, payloadFile(metadata.id))
        return metadata
    }

    private fun reconcilePayloadLocked(metadata: UploadMetadata, payload: File) {
        if (!payload.exists()) {
            require(metadata.committedBytes == 0L) { "upload payload is missing" }
            return
        }
        require(payload.isFile && payload.length() >= metadata.committedBytes) { "upload payload is shorter than committed progress" }
        if (payload.length() > metadata.committedBytes) {
            RandomAccessFile(payload, "rw").use { file -> file.setLength(metadata.committedBytes); file.fd.sync() }
        }
    }

    private fun publishLocked(metadata: UploadMetadata, payload: File) {
        if (published(metadata.artifactId, metadata.sha256, metadata.expectedSizeBytes)) {
            check(payload.delete() || !payload.exists()) { "duplicate upload staging payload could not be removed" }
            return
        }
        val versionPayload = File(artifactsRoot, "versions/${metadata.artifactId}/${metadata.sha256}/payload")
        val versionDirectory = requireNotNull(versionPayload.parentFile)
        check(versionDirectory.mkdirs() || versionDirectory.isDirectory)
        Files.move(payload.toPath(), versionPayload.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
        val manifest = File(artifactsRoot, "${metadata.artifactId}.manifest.json")
        val temporary = File(artifactsRoot, ".${metadata.artifactId}.upload-manifest.part")
        try {
            val value = JSONObject()
                .put("version", 1)
                .put("sha256", metadata.sha256)
                .put("sizeBytes", metadata.expectedSizeBytes)
                .put("relativePath", "versions/${metadata.artifactId}/${metadata.sha256}/payload")
            FileOutputStream(temporary).use { output -> output.write(value.toString().toByteArray()); output.fd.sync() }
            Files.move(temporary.toPath(), manifest.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
        } finally {
            temporary.delete()
        }
    }

    private fun published(artifactId: String, digest: String, expectedSize: Long): Boolean {
        val manifest = File(artifactsRoot, "$artifactId.manifest.json")
        val payload = File(artifactsRoot, "versions/$artifactId/$digest/payload")
        if (!manifest.isFile || manifest.length() !in 1..MAX_METADATA_BYTES || !payload.isFile || payload.length() != expectedSize) return false
        val value = runCatching { JSONObject(manifest.readText()) }.getOrNull() ?: return false
        if (value.optInt("version") != 1 || value.optString("sha256") != digest ||
            value.optLong("sizeBytes") != expectedSize || value.optString("relativePath") != "versions/$artifactId/$digest/payload"
        ) return false
        return sha256(payload) == digest
    }

    private fun preflightLocked(expectedBytes: Long) {
        require(artifactsRoot.mkdirs() || artifactsRoot.isDirectory) { "artifact directory unavailable" }
        require(uploadsRoot.mkdirs() || uploadsRoot.isDirectory) { "upload directory unavailable" }
        require(artifactsRoot.usableSpace >= expectedBytes + MIN_FREE_BYTES) { "insufficient free space for upload" }
        val retained = artifactsRoot.walkTopDown().filter(File::isFile).take(MAX_ARTIFACT_FILES + 1).toList()
        require(retained.size <= MAX_ARTIFACT_FILES) { "artifact file quota exceeded" }
        val reserved = uploadDirectoriesLocked().map(::readMetadataLocked)
            .filter { it.state == ArtifactUploadState.OPEN }
            .sumOf { it.expectedSizeBytes }
        require(retained.sumOf(File::length) + reserved + expectedBytes <= ARTIFACT_QUOTA_BYTES) { "artifact byte quota exceeded" }
    }

    private fun collectStaleLocked() {
        val now = clockMillis()
        uploadDirectoriesLocked().forEach { directory ->
            val metadata = readMetadataLocked(directory)
            if (now - metadata.updatedAtEpochMs < STALE_AFTER_MILLIS) return@forEach
            if (metadata.state == ArtifactUploadState.OPEN) {
                payloadFile(metadata.id).delete()
                writeMetadataLocked(metadata.copy(state = ArtifactUploadState.CANCELLED, updatedAtEpochMs = now))
            } else {
                deleteBounded(directory, MAX_DELETE_ENTRIES)
            }
        }
    }

    private fun cleanupInterruptedPublicationsLocked() {
        if (!artifactsRoot.isDirectory) return
        artifactsRoot.listFiles()?.filter { it.isFile && it.name.startsWith('.') && it.name.endsWith(".part") }
            ?.take(MAX_UPLOADS + 1)?.forEach { check(it.delete()) { "interrupted upload publication could not be removed" } }
    }

    private fun uploadDirectoriesLocked(): List<File> {
        ensureRoots()
        val values = uploadsRoot.listFiles()?.filter(File::isDirectory)?.sortedBy(File::getName).orEmpty()
        require(values.size <= MAX_UPLOADS) { "upload directory count exceeded bound" }
        return values
    }

    private fun readMetadataLocked(directory: File): UploadMetadata {
        val file = File(directory, METADATA_NAME)
        require(file.isFile && file.length() in 1..MAX_METADATA_BYTES) { "upload metadata is missing or out of bounds" }
        val value = JSONObject(file.readText())
        require(value.keys().asSequence().toSet() == METADATA_KEYS) { "upload metadata fields are invalid" }
        val metadata = UploadMetadata(
            id = value.getString("id"),
            artifactId = value.getString("artifactId"),
            sha256 = value.getString("sha256"),
            expectedSizeBytes = value.getLong("expectedSizeBytes"),
            committedBytes = value.getLong("committedBytes"),
            state = ArtifactUploadState.valueOf(value.getString("state")),
            idempotencyKey = value.getString("idempotencyKey"),
            requestDigest = value.getString("requestDigest"),
            createdAtEpochMs = value.getLong("createdAtEpochMs"),
            updatedAtEpochMs = value.getLong("updatedAtEpochMs"),
        )
        require(directory.name == metadata.id) { "upload directory does not match metadata id" }
        return metadata.validated()
    }

    private fun writeMetadataLocked(metadata: UploadMetadata) {
        metadata.validated()
        val directory = uploadDirectory(metadata.id)
        check(directory.mkdirs() || directory.isDirectory)
        val target = File(directory, METADATA_NAME)
        val temporary = File(directory, ".$METADATA_NAME.part")
        val value = JSONObject()
            .put("version", 1)
            .put("id", metadata.id)
            .put("artifactId", metadata.artifactId)
            .put("sha256", metadata.sha256)
            .put("expectedSizeBytes", metadata.expectedSizeBytes)
            .put("committedBytes", metadata.committedBytes)
            .put("state", metadata.state.name)
            .put("idempotencyKey", metadata.idempotencyKey)
            .put("requestDigest", metadata.requestDigest)
            .put("createdAtEpochMs", metadata.createdAtEpochMs)
            .put("updatedAtEpochMs", metadata.updatedAtEpochMs)
        try {
            FileOutputStream(temporary).use { output -> output.write(value.toString().toByteArray()); output.fd.sync() }
            Files.move(temporary.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
        } finally {
            temporary.delete()
        }
    }

    private fun UploadMetadata.validated(): UploadMetadata {
        HostArtifactUpload(id, artifactId, sha256, expectedSizeBytes, committedBytes, state)
        validateKey(idempotencyKey)
        require(SHA256.matches(requestDigest)) { "invalid upload request digest" }
        require(createdAtEpochMs >= 0 && updatedAtEpochMs >= createdAtEpochMs) { "invalid upload timestamps" }
        return this
    }

    private fun UploadMetadata.resource() = HostArtifactUpload(id, artifactId, sha256, expectedSizeBytes, committedBytes, state)
    private fun UploadMetadata.image() = HostImage(artifactId, sha256, expectedSizeBytes)
    private fun uploadDirectory(id: String) = File(uploadsRoot, id)
    private fun payloadFile(id: String) = File(uploadDirectory(id), PAYLOAD_NAME)
    private fun ensureRoots() { check(uploadsRoot.mkdirs() || uploadsRoot.isDirectory); check(artifactsRoot.mkdirs() || artifactsRoot.isDirectory) }
    private fun validateUploadId(id: String) { require(UPLOAD_ID.matches(id)) { "invalid upload id" } }
    private fun validateKey(key: String) { require(key.length in 16..200 && key.all { it.code in 0x21..0x7e }) { "invalid idempotency key" } }

    private fun deleteBounded(root: File, remaining: Int): Int {
        if (!root.exists()) return remaining
        require(remaining > 0) { "upload cleanup exceeded entry bound" }
        var budget = remaining - 1
        root.listFiles()?.forEach { budget = deleteBounded(it, budget) }
        check(root.delete()) { "upload path could not be removed" }
        return budget
    }

    private fun sha256(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(BUFFER_BYTES)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private data class UploadMetadata(
        val id: String,
        val artifactId: String,
        val sha256: String,
        val expectedSizeBytes: Long,
        val committedBytes: Long,
        val state: ArtifactUploadState,
        val idempotencyKey: String,
        val requestDigest: String,
        val createdAtEpochMs: Long,
        val updatedAtEpochMs: Long,
    )

    private companion object {
        val UPLOAD_ID = Regex("upload-[a-f0-9]{32}")
        val SHA256 = Regex("[a-f0-9]{64}")
        val METADATA_KEYS = setOf("version", "id", "artifactId", "sha256", "expectedSizeBytes", "committedBytes", "state", "idempotencyKey", "requestDigest", "createdAtEpochMs", "updatedAtEpochMs")
        const val METADATA_NAME = "metadata.json"
        const val PAYLOAD_NAME = "payload.part"
        const val MAX_UPLOADS = 16
        const val MAX_CHUNK_BYTES = 1024 * 1024
        const val MAX_CANONICAL_BYTES = 64 * 1024
        const val MAX_METADATA_BYTES = 8192L
        const val MAX_DELETE_ENTRIES = 8
        const val MAX_ARTIFACT_FILES = 512
        const val ARTIFACT_QUOTA_BYTES = 96L * 1024 * 1024 * 1024
        const val MIN_FREE_BYTES = 256L * 1024 * 1024
        const val STALE_AFTER_MILLIS = 24L * 60 * 60 * 1000
        const val BUFFER_BYTES = 64 * 1024
    }
}

/** Adds upload discovery without changing the production resource-query implementation. */
internal class ArtifactUploadResourceQueries(private val delegate: HostResourceQueries) : HostResourceQueries {
    override suspend fun status(): HostStatus = delegate.status()
    override suspend fun capabilities(): List<HostCapability> =
        (delegate.capabilities() + HostCapability("image.resumable-upload", true)).distinctBy(HostCapability::id)
    override suspend fun profiles(): List<HostProfile> = delegate.profiles()
    override suspend fun images(): List<HostImage> = delegate.images()
    override suspend fun vms(): List<HostVm> = delegate.vms()
    override suspend fun vm(id: RuntimeId): HostVm? = delegate.vm(id)
    override suspend fun operations(): List<OperationRecord> = delegate.operations()
    override suspend fun operation(id: String): OperationRecord? = delegate.operation(id)
    override suspend fun diagnostics(): HostDiagnostics = delegate.diagnostics()
}

private fun secureUploadId(): String {
    val bytes = ByteArray(16).also(SecureRandom()::nextBytes)
    return "upload-" + bytes.joinToString("") { "%02x".format(it) }
}
