package org.nodehost.api

import java.util.ArrayDeque
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.ControllerAuthenticator
import org.nodehost.core.ControllerPrincipal
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.OperationRecord
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId

class HostApiConflictException(message: String) : RuntimeException(message)
class HostApiRateLimitException(message: String) : RuntimeException(message)

data class ApplyVmRequest(
    val id: String,
    val generation: Long,
    val desiredState: String,
    val profileId: String,
    val memoryMiB: Int,
    val vcpus: Int,
    val dataDiskGiB: Int,
    val preserveOnDelete: Boolean,
)

/** Typed Host API application adapter. It never accepts shell, QMP, or argv fields. */
class HostApiController(
    private val authenticator: ControllerAuthenticator,
    private val queries: HostResourceQueries,
    private val mutations: HostMutationUseCases,
    private val applyRuntime: ApplyRuntimeUseCase,
    private val recoverySsh: RecoverySshGateway,
    private val acceptedOperationDispatcher: AcceptedOperationDispatcher = AcceptedOperationDispatcher.UNCONFIGURED,
    private val artifactUploads: ArtifactUploadUseCases = ArtifactUploadUseCases.UNCONFIGURED,
    private val monotonicNanos: () -> Long = System::nanoTime,
    private val recoveryMaxStartsPerMinute: Int = RECOVERY_MAX_STARTS_PER_MINUTE,
) {
    private val recoveryLock = Mutex()
    private val recoveryStarts = ArrayDeque<Long>()
    private var recoveryActive = false

    init { require(recoveryMaxStartsPerMinute > 0) }

    suspend fun authorize(header: String?, method: String, path: String): ControllerPrincipal? =
        authenticator.authorize(header, method, path)

    suspend fun status() = queries.status()
    suspend fun capabilities() = queries.capabilities().take(MAX_CAPABILITIES)
    suspend fun profiles() = queries.profiles().take(MAX_PROFILES)
    suspend fun images() = queries.images().take(MAX_IMAGES)
    suspend fun vms() = queries.vms().take(MAX_VMS)
    suspend fun vm(id: String): HostVm? = queries.vm(requireDefaultRuntime(id))
    suspend fun operations() = queries.operations().take(MAX_OPERATIONS)
    suspend fun operation(id: String): OperationRecord? { validateId(id); return queries.operation(id) }
    suspend fun diagnostics() = queries.diagnostics()

    suspend fun createArtifactUpload(
        request: ArtifactUploadCreateRequest,
        idempotencyKey: String,
        canonicalRequest: ByteArray,
    ): HostArtifactUpload {
        validateKey(idempotencyKey)
        require(canonicalRequest.isNotEmpty() && canonicalRequest.size <= MAX_REQUEST_BYTES) { "canonical request is out of bounds" }
        return artifactUploads.createUpload(request, idempotencyKey, canonicalRequest)
    }

    suspend fun artifactUpload(id: String): HostArtifactUpload? {
        validateUploadId(id)
        return artifactUploads.upload(id)
    }

    suspend fun writeArtifactChunk(id: String, offset: Long, chunkSha256: String, bytes: ByteArray): HostArtifactUpload {
        validateUploadId(id)
        require(offset >= 0) { "upload offset must be non-negative" }
        require(SHA256.matches(chunkSha256)) { "invalid chunk digest" }
        require(bytes.size in 1..MAX_UPLOAD_CHUNK_BYTES) { "upload chunk size is out of range" }
        return artifactUploads.writeChunk(id, offset, chunkSha256, bytes)
    }

    suspend fun completeArtifactUpload(id: String): HostImage {
        validateUploadId(id)
        return artifactUploads.completeUpload(id)
    }

    suspend fun cancelArtifactUpload(id: String): HostArtifactUpload {
        validateUploadId(id)
        return artifactUploads.cancelUpload(id)
    }

    suspend fun importImage(request: ImageImportRequest, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord {
        validateKey(idempotencyKey)
        require(request.sourceUrl.startsWith("https://")) { "image source must use HTTPS" }
        require(SHA256.matches(request.sha256)) { "invalid image digest" }
        require(request.expectedSizeBytes in 1..MAX_IMAGE_BYTES) { "image size is out of range" }
        return mutations.importImage(request, idempotencyKey, canonicalRequest)
    }

    suspend fun applyVm(request: ApplyVmRequest, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord {
        validateKey(idempotencyKey)
        val runtimeId = requireDefaultRuntime(request.id)
        val desired = RuntimeSpec(
            id = runtimeId,
            generation = request.generation,
            desiredState = DesiredRuntimeState.valueOf(request.desiredState.uppercase()),
            profileId = VmProfileId(request.profileId),
            memoryMiB = request.memoryMiB,
            vcpus = request.vcpus,
            dataDiskGiB = request.dataDiskGiB,
            preserveDataOnDelete = request.preserveOnDelete,
        )
        val operation = applyRuntime.apply(desired, idempotencyKey, canonicalRequest)
        acceptedOperationDispatcher.dispatch(operation)
        return operation
    }

    suspend fun removeVm(id: String, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord {
        validateKey(idempotencyKey)
        val operation = mutations.removeVm(requireDefaultRuntime(id), idempotencyKey, canonicalRequest)
        acceptedOperationDispatcher.dispatch(operation)
        return operation
    }

    suspend fun cancelOperation(id: String, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord {
        validateId(id); validateKey(idempotencyKey)
        val operation = mutations.cancelOperation(id, idempotencyKey, canonicalRequest)
        acceptedOperationDispatcher.dispatch(operation)
        return operation
    }

    suspend fun revokeController(id: String, idempotencyKey: String, canonicalRequest: ByteArray) {
        validateId(id); validateKey(idempotencyKey)
        mutations.revokeController(id, idempotencyKey, canonicalRequest)
    }

    suspend fun openRecovery(vmId: String, principal: ControllerPrincipal): RecoverySshSession {
        val id = requireDefaultRuntime(vmId)
        val delegate = recoveryLock.withLock {
            if (recoveryActive) throw HostApiConflictException("recovery SSH session already active")
            val now = monotonicNanos()
            val cutoff = now - RECOVERY_RATE_WINDOW_NANOS
            while (recoveryStarts.isNotEmpty() && recoveryStarts.first() <= cutoff) recoveryStarts.removeFirst()
            if (recoveryStarts.size >= recoveryMaxStartsPerMinute) {
                throw HostApiRateLimitException("recovery SSH session start rate exceeded")
            }
            val opened = recoverySsh.open(id, principal)
            recoveryStarts.addLast(now)
            recoveryActive = true
            opened
        }
        return object : RecoverySshSession {
            private val closeLock = Mutex()
            private var closed = false
            override suspend fun read(maxBytes: Int): ByteArray? = delegate.read(maxBytes)
            override suspend fun write(bytes: ByteArray) = delegate.write(bytes)
            override suspend fun close() = closeLock.withLock {
                if (closed) return@withLock
                try { delegate.close() } finally {
                    recoveryLock.withLock { recoveryActive = false }
                    closed = true
                }
            }
        }
    }

    private fun requireDefaultRuntime(id: String): RuntimeId {
        require(RuntimeId(id) == RuntimeId.DEFAULT) { "MVP supports only the default runtime" }
        return RuntimeId.DEFAULT
    }
    private fun validateId(value: String) { require(ID.matches(value)) { "invalid resource identifier" } }
    private fun validateUploadId(value: String) { require(UPLOAD_ID.matches(value)) { "invalid upload identifier" } }
    private fun validateKey(value: String) {
        require(value.length in 16..200 && value.all { it.code in 0x21..0x7e }) { "invalid idempotency key" }
    }

    companion object {
        const val MAX_REQUEST_BYTES = 1024 * 1024
        const val MAX_UPLOAD_CHUNK_BYTES = 1024 * 1024
        const val MAX_IMAGE_BYTES = 64L * 1024 * 1024 * 1024
        const val MAX_CAPABILITIES = 128
        const val MAX_PROFILES = 32
        const val MAX_IMAGES = 128
        const val MAX_VMS = 1
        const val MAX_OPERATIONS = 256
        const val RECOVERY_MAX_STARTS_PER_MINUTE = 6
        const val RECOVERY_RATE_WINDOW_NANOS = 60_000_000_000L
        val SHA256 = Regex("[a-f0-9]{64}")
        val UPLOAD_ID = Regex("[A-Za-z0-9][A-Za-z0-9._-]{2,127}")
        private val ID = Regex("[A-Za-z0-9][A-Za-z0-9._-]{2,127}")
    }
}
