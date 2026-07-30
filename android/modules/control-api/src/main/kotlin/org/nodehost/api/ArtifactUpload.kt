package org.nodehost.api

/** Durable staging resource for controller-to-host artifact transfer. */
enum class ArtifactUploadState { OPEN, COMPLETED, CANCELLED }

data class ArtifactUploadCreateRequest(
    val artifactId: String,
    val sha256: String,
    val expectedSizeBytes: Long,
) {
    init {
        require(ARTIFACT_ID.matches(artifactId)) { "invalid artifactId" }
        require(HostApiController.SHA256.matches(sha256)) { "invalid sha256" }
        require(expectedSizeBytes in 1..HostApiController.MAX_IMAGE_BYTES) { "expectedSizeBytes is out of range" }
    }

    companion object { val ARTIFACT_ID = Regex("[a-z0-9][a-z0-9.-]{0,127}") }
}

data class HostArtifactUpload(
    val id: String,
    val artifactId: String,
    val sha256: String,
    val expectedSizeBytes: Long,
    val committedBytes: Long,
    val state: ArtifactUploadState,
) {
    init {
        require(HostApiController.UPLOAD_ID.matches(id)) { "invalid upload id" }
        ArtifactUploadCreateRequest(artifactId, sha256, expectedSizeBytes)
        require(committedBytes in 0..expectedSizeBytes) { "committedBytes is out of range" }
        if (state == ArtifactUploadState.COMPLETED) require(committedBytes == expectedSizeBytes)
    }
}

/**
 * Upload semantics are intentionally sequential for the MVP. Exact replay of an already committed
 * chunk is idempotent; gaps, partial overlaps, and conflicting replay are rejected.
 */
interface ArtifactUploadUseCases {
    suspend fun createUpload(
        request: ArtifactUploadCreateRequest,
        idempotencyKey: String,
        canonicalRequest: ByteArray,
    ): HostArtifactUpload

    suspend fun upload(id: String): HostArtifactUpload?
    suspend fun writeChunk(id: String, offset: Long, chunkSha256: String, bytes: ByteArray): HostArtifactUpload
    suspend fun completeUpload(id: String): HostImage
    suspend fun cancelUpload(id: String): HostArtifactUpload

    companion object {
        val UNCONFIGURED = object : ArtifactUploadUseCases {
            override suspend fun createUpload(request: ArtifactUploadCreateRequest, idempotencyKey: String, canonicalRequest: ByteArray) = error("artifact upload adapter is not configured")
            override suspend fun upload(id: String): HostArtifactUpload? = error("artifact upload adapter is not configured")
            override suspend fun writeChunk(id: String, offset: Long, chunkSha256: String, bytes: ByteArray) = error("artifact upload adapter is not configured")
            override suspend fun completeUpload(id: String): HostImage = error("artifact upload adapter is not configured")
            override suspend fun cancelUpload(id: String): HostArtifactUpload = error("artifact upload adapter is not configured")
        }
    }
}
