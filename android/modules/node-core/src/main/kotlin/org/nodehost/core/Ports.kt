package org.nodehost.core

import org.nodehost.model.*

data class OperationContext(val operationId: OperationId, val stepId: String, val attempt: Int) {
    init {
        require(Regex("[a-z][a-z0-9_.-]{0,127}").matches(stepId))
        require(attempt in 1..100)
    }
}

data class StepOutcome(val changed: Boolean, val observationHint: String? = null)
data class ResolvedArtifact(val localPath: String, val sha256: String, val sizeBytes: Long)
data class HostMeshConfiguration(val controlUrl: String, val hostname: String, val oneUseAuthKey: SensitiveValue)

data class HostMeshStatus(val state: State, val addresses: List<String> = emptyList(), val detail: String? = null) {
    enum class State { STOPPED, NEEDS_PERMISSION, ENROLLING, RUNNING, ERROR }
}

sealed interface DesiredRuntimeAcceptance {
    data object Accepted : DesiredRuntimeAcceptance
    data class Replay(val operation: OperationRecord) : DesiredRuntimeAcceptance
    data object IdempotencyConflict : DesiredRuntimeAcceptance
    data class GenerationRejected(val decision: GenerationDecision) : DesiredRuntimeAcceptance
}

sealed interface EnrollmentAcceptance {
    data object Accepted : EnrollmentAcceptance
    data class Replay(val operation: OperationRecord) : EnrollmentAcceptance
    data object IdempotencyConflict : EnrollmentAcceptance
    data object EnrollmentConflict : EnrollmentAcceptance
}

interface RuntimeBackend {
    suspend fun observe(id: RuntimeId): RuntimeObservation
    suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome
}

interface OperationRepository {
    suspend fun load(id: OperationId): OperationRecord?
    suspend fun save(record: OperationRecord)
    suspend fun loadDesiredRuntime(id: RuntimeId): RuntimeSpec?

    /**
     * Atomically checks the idempotency key and generation, then persists desired state and operation.
     * Implementations must return the original operation for an exact key/digest replay.
     */
    suspend fun acceptDesiredRuntime(spec: RuntimeSpec, operation: OperationRecord): DesiredRuntimeAcceptance
}

interface EnrollmentRepository {
    suspend fun load(): NodeEnrollment?

    /** Atomically checks idempotency/enrollment identity and persists the enrollment and operation. */
    suspend fun acceptEnrollment(enrollment: NodeEnrollment, operation: OperationRecord): EnrollmentAcceptance
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
