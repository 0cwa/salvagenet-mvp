package org.nodehost.core

import org.nodehost.model.NodeEnrollment
import org.nodehost.model.OperationRecord
import org.nodehost.model.OperationState

class ImportEnrollmentUseCase(
    private val enrollments: EnrollmentRepository,
    private val operationIds: OperationIdFactory,
    private val clock: Clock,
) {
    suspend fun import(
        enrollment: NodeEnrollment,
        idempotencyKey: String,
        canonicalRequest: ByteArray,
    ): OperationRecord {
        validateMutationInput(idempotencyKey, canonicalRequest)
        require(enrollment.expiresAtEpochMs > clock.epochMillis()) { "enrollment has expired" }

        val operation = OperationRecord(
            id = operationIds.newId(),
            idempotencyKey = idempotencyKey,
            requestDigest = requestDigest(canonicalRequest),
            runtimeId = null,
            desiredGeneration = null,
            state = OperationState.ACCEPTED,
            currentStepId = null,
        )
        return when (val result = enrollments.acceptEnrollment(enrollment, operation)) {
            EnrollmentAcceptance.Accepted -> operation
            is EnrollmentAcceptance.Replay -> result.operation.also {
                require(
                    it.idempotencyKey == operation.idempotencyKey &&
                        it.requestDigest == operation.requestDigest &&
                        it.runtimeId == null &&
                        it.desiredGeneration == null,
                ) { "repository returned an invalid replay" }
            }
            EnrollmentAcceptance.IdempotencyConflict ->
                throw IllegalArgumentException("idempotency key reused with different request")
            EnrollmentAcceptance.EnrollmentConflict ->
                throw IllegalArgumentException("a different enrollment is already installed")
        }
    }
}
