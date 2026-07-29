package org.nodehost.store

import androidx.room.withTransaction
import org.nodehost.core.Clock
import org.nodehost.core.DesiredRuntimeAcceptance
import org.nodehost.core.OperationRepository
import org.nodehost.core.StepOutcome
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.GenerationDecision
import org.nodehost.model.OperationId
import org.nodehost.model.OperationRecord
import org.nodehost.model.OperationState
import org.nodehost.model.RuntimeGenerationRules
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId

/** Room's transaction is the serialization boundary for desired generations and idempotency keys. */
class RoomOperationRepository(
    private val database: NodeHostDatabase,
    private val clock: Clock,
) : OperationRepository {
    private val dao get() = database.dao()

    override suspend fun load(id: OperationId): OperationRecord? = dao.operation(id.value)?.toModel()

    override suspend fun save(record: OperationRecord) {
        database.withTransaction {
            val existing = checkNotNull(dao.operation(record.id.value)) { "operation does not exist" }
            dao.updateOperation(record.toEntity(existing.createdAtEpochMillis, clock.epochMillis()))
        }
    }

    override suspend fun loadDesiredRuntime(id: RuntimeId): RuntimeSpec? = dao.desired(id.value)?.toModel()

    override suspend fun acceptDesiredRuntime(
        spec: RuntimeSpec,
        operation: OperationRecord,
    ): DesiredRuntimeAcceptance = database.withTransaction {
        dao.operationByKey(operation.idempotencyKey)?.let { existing ->
            return@withTransaction if (existing.requestDigest == operation.requestDigest) {
                DesiredRuntimeAcceptance.Replay(existing.toModel())
            } else {
                DesiredRuntimeAcceptance.IdempotencyConflict
            }
        }

        require(dao.operationCount() < MAX_RETAINED_OPERATIONS) { "operation journal capacity exceeded" }
        val current = dao.desired(spec.id.value)?.toModel()
        val decision = RuntimeGenerationRules.decide(current, spec)
        if (decision !in setOf(GenerationDecision.INITIAL, GenerationDecision.ADVANCE)) {
            return@withTransaction DesiredRuntimeAcceptance.GenerationRejected(decision)
        }

        if (current == null) dao.insertDesired(spec.toEntity()) else dao.updateDesired(spec.toEntity())
        val now = clock.epochMillis()
        dao.insertOperation(operation.toEntity(now, now))
        DesiredRuntimeAcceptance.Accepted
    }

    suspend fun operationForDesired(spec: RuntimeSpec): OperationRecord? =
        dao.operationForGeneration(spec.id.value, spec.generation)?.toModel()

    suspend fun current(id: RuntimeId): RuntimeObservation? = dao.current(id.value)?.toModel()

    suspend fun recordObservation(observation: RuntimeObservation) {
        dao.putCurrent(observation.toEntity(clock.epochMillis()))
    }

    /** Persists an inspectable intent before an effect. A STARTED row is reused after process death. */
    suspend fun beginStep(
        operation: OperationRecord,
        stepId: String,
        repeatCompleted: Boolean = false,
    ): OperationStepEntity = database.withTransaction {
        val latest = dao.latestStep(operation.id.value, stepId)
        if (latest?.status == StepStatus.STARTED.name) return@withTransaction latest
        if (!repeatCompleted && latest?.status == StepStatus.SUCCEEDED.name) return@withTransaction latest
        val attempt = (latest?.attempt ?: 0) + 1
        require(attempt <= MAX_STEP_ATTEMPTS) { "step attempt limit exceeded" }
        val now = clock.epochMillis()
        val intent = OperationStepEntity(
            operationId = operation.id.value,
            stepId = stepId,
            attempt = attempt,
            status = StepStatus.STARTED.name,
            startedAtEpochMillis = now,
            finishedAtEpochMillis = null,
            changed = null,
            resultDetail = null,
            errorCode = null,
        )
        dao.insertStep(intent)
        val stored = checkNotNull(dao.operation(operation.id.value))
        dao.updateOperation(stored.copy(currentStepId = stepId, updatedAtEpochMillis = now))
        intent
    }

    suspend fun completeStep(intent: OperationStepEntity, outcome: StepOutcome) = database.withTransaction {
        require(intent.status == StepStatus.STARTED.name)
        dao.updateStep(
            intent.copy(
                status = StepStatus.SUCCEEDED.name,
                finishedAtEpochMillis = clock.epochMillis(),
                changed = outcome.changed,
                resultDetail = outcome.observationHint?.take(MAX_RESULT_DETAIL_CHARS),
            ),
        )
    }

    suspend fun failStep(intent: OperationStepEntity, errorCode: String) = database.withTransaction {
        require(ERROR_CODE.matches(errorCode))
        val now = clock.epochMillis()
        dao.updateStep(intent.copy(status = StepStatus.FAILED.name, finishedAtEpochMillis = now, errorCode = errorCode))
        val stored = checkNotNull(dao.operation(intent.operationId))
        dao.updateOperation(stored.copy(state = OperationState.FAILED_RETRYABLE.name, errorCode = errorCode, updatedAtEpochMillis = now))
    }

    suspend fun markSucceeded(operation: OperationRecord) = database.withTransaction {
        val stored = checkNotNull(dao.operation(operation.id.value))
        dao.updateOperation(stored.copy(state = OperationState.SUCCEEDED.name, currentStepId = null, errorCode = null, updatedAtEpochMillis = clock.epochMillis()))
    }

    suspend fun steps(operationId: OperationId): List<OperationStepEntity> = dao.steps(operationId.value)

    companion object {
        const val MAX_STEP_ATTEMPTS = 100
        const val MAX_RETAINED_OPERATIONS = 10_000L
        private const val MAX_RESULT_DETAIL_CHARS = 512
        private val ERROR_CODE = Regex("[A-Z][A-Z0-9_]{0,63}")
    }
}

enum class StepStatus { STARTED, SUCCEEDED, FAILED }

private fun RuntimeSpec.toEntity() = DesiredRuntimeEntity(
    id.value, generation, desiredState.name, profileId.value, memoryMiB, vcpus, dataDiskGiB, preserveDataOnDelete,
)

private fun DesiredRuntimeEntity.toModel() = RuntimeSpec(
    RuntimeId(runtimeId), generation, DesiredRuntimeState.valueOf(state), VmProfileId(profileId),
    memoryMiB, vcpus, dataDiskGiB, preserveDataOnDelete,
)

private fun OperationRecord.toEntity(createdAt: Long, updatedAt: Long) = OperationEntity(
    id.value, idempotencyKey, requestDigest, runtimeId?.value, desiredGeneration, state.name,
    currentStepId, errorCode, createdAt, updatedAt,
)

private fun OperationEntity.toModel() = OperationRecord(
    OperationId(id), idempotencyKey, requestDigest, runtimeId?.let(::RuntimeId), desiredGeneration,
    OperationState.valueOf(state), currentStepId, errorCode,
)

private fun RuntimeObservation.toEntity(observedAt: Long): CurrentRuntimeEntity = when (this) {
    is RuntimeObservation.Absent -> CurrentRuntimeEntity(id.value, "ABSENT", null, null, null, null, null, observedAt)
    is RuntimeObservation.Stopped -> CurrentRuntimeEntity(id.value, "STOPPED", profileId?.value, null, null, null, null, observedAt)
    is RuntimeObservation.Starting -> CurrentRuntimeEntity(id.value, "STARTING", null, processId, null, null, null, observedAt)
    is RuntimeObservation.Running -> CurrentRuntimeEntity(id.value, "RUNNING", null, processId, guestReady, null, null, observedAt)
    is RuntimeObservation.Stopping -> CurrentRuntimeEntity(id.value, "STOPPING", null, processId, null, gracefulDeadlineExceeded, null, observedAt)
    is RuntimeObservation.Failed -> CurrentRuntimeEntity(id.value, "FAILED", null, null, null, null, "$code:${if (retryable) 1 else 0}", observedAt)
    is RuntimeObservation.Unknown -> CurrentRuntimeEntity(id.value, "UNKNOWN", null, null, null, null, reason.take(512), observedAt)
}

private fun CurrentRuntimeEntity.toModel(): RuntimeObservation = when (kind) {
    "ABSENT" -> RuntimeObservation.Absent(RuntimeId(runtimeId))
    "STOPPED" -> RuntimeObservation.Stopped(RuntimeId(runtimeId), profileId?.let(::VmProfileId))
    "STARTING" -> RuntimeObservation.Starting(RuntimeId(runtimeId), processId)
    "RUNNING" -> RuntimeObservation.Running(RuntimeId(runtimeId), processId, guestReady == true)
    "STOPPING" -> RuntimeObservation.Stopping(RuntimeId(runtimeId), processId, gracefulDeadlineExceeded == true)
    "FAILED" -> RuntimeObservation.Failed(RuntimeId(runtimeId), detail.orEmpty().substringBefore(':'), detail?.endsWith(":1") == true)
    else -> RuntimeObservation.Unknown(RuntimeId(runtimeId), detail ?: "unrecognized durable observation")
}
