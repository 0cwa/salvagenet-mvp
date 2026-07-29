package org.nodehost.api

import org.nodehost.core.ControllerPrincipal
import org.nodehost.model.OperationRecord
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeSpec

/** Replaceable lifecycle port; transport security is owned by the composition root. */
interface HostApiServer {
    fun start(bindAddress: String, port: Int)
    fun stop()
}

data class HostStatus(val deviceId: String, val hostMesh: String, val runtime: String) {
    init {
        require(deviceId.length in 1..128)
        require(hostMesh.length in 1..64 && runtime.length in 1..64)
    }
}
data class HostCapability(val id: String, val supported: Boolean, val detail: String? = null) {
    init {
        require(Regex("[a-z][a-z0-9.-]{0,63}").matches(id))
        require(detail == null || detail.length <= 256)
    }
}
data class HostProfile(val id: String, val version: Int, val bootKind: String) {
    init {
        require(Regex("[a-z0-9][a-z0-9-]{0,63}").matches(id) && version >= 1)
        require(bootKind in setOf("DIRECT_KERNEL", "UEFI"))
    }
}
data class HostImage(val id: String, val sha256: String, val sizeBytes: Long) {
    init {
        require(Regex("[a-z0-9][a-z0-9.-]{0,127}").matches(id))
        require(Regex("[a-f0-9]{64}").matches(sha256))
        require(sizeBytes in 1..HostApiController.MAX_IMAGE_BYTES)
    }
}
data class HostVm(
    val id: String,
    val generation: Long,
    val desiredState: String,
    val profileId: String,
    val memoryMiB: Int,
    val vcpus: Int,
    val dataDiskGiB: Int,
) {
    init {
        require(RuntimeId(id) == RuntimeId.DEFAULT) { "MVP supports only the default runtime" }
        RuntimeSpec(
            id = RuntimeId.DEFAULT, generation = generation,
            desiredState = org.nodehost.model.DesiredRuntimeState.valueOf(desiredState.uppercase()),
            profileId = org.nodehost.model.VmProfileId(profileId), memoryMiB = memoryMiB,
            vcpus = vcpus, dataDiskGiB = dataDiskGiB,
        )
    }
}
data class HostDiagnostics(val generatedAtEpochMs: Long, val entries: Map<String, String>) {
    init { require(generatedAtEpochMs >= 0) }
}

data class ImageImportRequest(val sourceUrl: String, val sha256: String, val expectedSizeBytes: Long)

/** Bounded read resources. Implementations must return no more than the documented maxima. */
interface HostResourceQueries {
    suspend fun status(): HostStatus
    suspend fun capabilities(): List<HostCapability>
    suspend fun profiles(): List<HostProfile>
    suspend fun images(): List<HostImage>
    suspend fun vms(): List<HostVm>
    suspend fun vm(id: RuntimeId): HostVm?
    suspend fun operations(): List<OperationRecord>
    suspend fun operation(id: String): OperationRecord?
    suspend fun diagnostics(): HostDiagnostics
}

/**
 * Mutations not yet represented by ApplyRuntimeUseCase remain explicit ports.
 * Adapters must apply node-core's atomic idempotency rules before effects. Image
 * adapters additionally enforce a download deadline, verify every redirect and
 * resolved address against their artifact-source policy, stream to a bounded
 * temporary file, and publish only after exact size and SHA-256 verification.
 */
interface HostMutationUseCases {
    suspend fun importImage(request: ImageImportRequest, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord
    suspend fun removeVm(id: RuntimeId, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord
    suspend fun cancelOperation(id: String, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord
    suspend fun revokeController(id: String, idempotencyKey: String, canonicalRequest: ByteArray)
}

/**
 * Post-persistence dispatch seam for durable runtime operations. Implementations may coalesce
 * duplicate notifications, but must not return until the accepted operation is guaranteed a wake.
 */
fun interface AcceptedOperationDispatcher {
    suspend fun dispatch(operation: OperationRecord)

    companion object {
        /** Source-compatible but fail-closed until T07 composition supplies its actor wake. */
        val UNCONFIGURED = AcceptedOperationDispatcher {
            error("accepted operation dispatcher is not configured")
        }
    }
}

/** A single authenticated, VM-scoped recovery stream; never an arbitrary forwarding target. */
interface RecoverySshGateway {
    suspend fun open(vmId: RuntimeId, principal: ControllerPrincipal): RecoverySshSession
}

/** Supports exactly one concurrent reader and one writer; close must unblock both. */
interface RecoverySshSession {
    suspend fun read(maxBytes: Int): ByteArray?
    suspend fun write(bytes: ByteArray)
    suspend fun close()
}
