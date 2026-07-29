package org.nodehost.core

import java.security.MessageDigest
import org.nodehost.model.OperationRecord
import org.nodehost.model.OperationState
import org.nodehost.model.RuntimeSpec

class ApplyRuntimeUseCase(
    private val operations: OperationRepository,
    private val operationIds: OperationIdFactory,
) {
    suspend fun apply(
        spec: RuntimeSpec,
        idempotencyKey: String,
        canonicalRequest: ByteArray,
    ): OperationRecord {
        require(idempotencyKey.length in 16..200)
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(canonicalRequest)
            .joinToString(separator = "") { byte -> "%02x".format(byte) }

        operations.findByIdempotencyKey(idempotencyKey)?.let { existing ->
            require(existing.requestDigest == digest) {
                "idempotency key reused with different request"
            }
            return existing
        }

        val current = operations.loadDesiredRuntime(spec.id)
        require(
            current == null ||
                spec.generation > current.generation ||
                (spec.generation == current.generation && spec == current),
        ) { "generation must advance when desired state changes" }

        val operation = OperationRecord(
            id = operationIds.newId(),
            idempotencyKey = idempotencyKey,
            requestDigest = digest,
            runtimeId = spec.id,
            desiredGeneration = spec.generation,
            state = OperationState.ACCEPTED,
            currentStepId = null,
        )
        operations.acceptDesiredRuntime(spec, operation)
        return operation
    }
}
