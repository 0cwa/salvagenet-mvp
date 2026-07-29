package org.nodehost.core

import org.nodehost.model.*

data class OperationContext(val operationId: OperationId, val stepId: String, val attempt: Int)
data class StepOutcome(val changed: Boolean, val observationHint: String? = null)
data class ResolvedArtifact(val localPath: String, val sha256: String, val sizeBytes: Long)
data class HostMeshConfiguration(val controlUrl: String, val hostname: String, val oneUseAuthKey: SecretValue)
@JvmInline value class SecretValue(val value: String) { override fun toString(): String = "<redacted>" }

data class HostMeshStatus(val state: State, val addresses: List<String> = emptyList(), val detail: String? = null) {
    enum class State { STOPPED, NEEDS_PERMISSION, ENROLLING, RUNNING, ERROR }
}

interface RuntimeBackend {
    suspend fun observe(id: RuntimeId): RuntimeObservation
    suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome
}
interface OperationRepository {
    suspend fun findByIdempotencyKey(key: String): OperationRecord?
    suspend fun load(id: OperationId): OperationRecord?
    suspend fun save(record: OperationRecord)
    suspend fun loadDesiredRuntime(id: RuntimeId): RuntimeSpec?
    /** Atomically persist desired state and its accepted operation. */
    suspend fun acceptDesiredRuntime(spec: RuntimeSpec, operation: OperationRecord)
}
interface ArtifactRepository { suspend fun resolve(ref: ArtifactRef): ResolvedArtifact }
interface ProfileRepository { suspend fun get(id: VmProfileId): VmProfile }
interface HostMesh {
    suspend fun configure(configuration: HostMeshConfiguration)
    suspend fun start()
    suspend fun stop()
    suspend fun status(): HostMeshStatus
    suspend fun clearIdentity()
}
interface ControllerAuthenticator { suspend fun authorize(authorization: String?, method: String, path: String): ControllerPrincipal? }
data class ControllerPrincipal(val id: String, val roles: Set<String>)
fun interface OperationIdFactory { fun newId(): OperationId }
interface Clock { fun epochMillis(): Long }
