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
        validateMutationInput(idempotencyKey, canonicalRequest)
        val operation = OperationRecord(
            id = operationIds.newId(),
            idempotencyKey = idempotencyKey,
            requestDigest = requestDigest(canonicalRequest),
            runtimeId = spec.id,
            desiredGeneration = spec.generation,
            state = OperationState.ACCEPTED,
            currentStepId = null,
        )

        return when (val result = operations.acceptDesiredRuntime(spec, operation)) {
            DesiredRuntimeAcceptance.Accepted -> operation
            is DesiredRuntimeAcceptance.Replay -> result.operation.also {
                require(
                    it.idempotencyKey == operation.idempotencyKey &&
                        it.requestDigest == operation.requestDigest &&
                        it.runtimeId == spec.id &&
                        it.desiredGeneration == spec.generation,
                ) { "repository returned an invalid replay" }
            }
            DesiredRuntimeAcceptance.IdempotencyConflict ->
                throw IllegalArgumentException("idempotency key reused with different request")
            is DesiredRuntimeAcceptance.GenerationRejected ->
                throw IllegalArgumentException("generation rejected: ${result.decision}")
        }
    }
}

internal const val MAX_CANONICAL_REQUEST_BYTES = 1_048_576

internal fun validateMutationInput(idempotencyKey: String, canonicalRequest: ByteArray) {
    require(idempotencyKey.length in 16..200) { "invalid idempotency key length" }
    require(canonicalRequest.isNotEmpty()) { "canonical request must not be empty" }
    require(canonicalRequest.size <= MAX_CANONICAL_REQUEST_BYTES) { "canonical request is too large" }
}

internal fun requestDigest(canonicalRequest: ByteArray): String =
    MessageDigest.getInstance("SHA-256")
        .digest(canonicalRequest)
        .joinToString(separator = "") { byte -> "%02x".format(byte) }
