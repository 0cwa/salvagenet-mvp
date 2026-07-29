package org.nodehost.model

@JvmInline value class OperationId(val value: String)

enum class OperationState {
    ACCEPTED, PREFLIGHT, FETCHING, VERIFYING, PREPARING_DISKS, PREPARING_BOOT,
    STARTING_QEMU, WAITING_FOR_QMP, BOOTSTRAPPING_GUEST, WAITING_FOR_SSH,
    WAITING_FOR_GUEST_MESH, SUCCEEDED, WAITING_FOR_USER, FAILED_RETRYABLE,
    FAILED_PERMANENT, CANCELLING, CANCELLED, ROLLING_BACK, ROLLED_BACK;

    val terminal: Boolean get() = this in setOf(SUCCEEDED, FAILED_PERMANENT, CANCELLED, ROLLED_BACK)
}

data class OperationRecord(
    val id: OperationId,
    val idempotencyKey: String,
    val requestDigest: String,
    val runtimeId: RuntimeId?,
    val desiredGeneration: Long?,
    val state: OperationState,
    val currentStepId: String?,
    val errorCode: String? = null,
)

object OperationTransitions {
    private val allowed = mapOf(
        OperationState.ACCEPTED to setOf(OperationState.PREFLIGHT, OperationState.CANCELLING),
        OperationState.PREFLIGHT to setOf(OperationState.FETCHING, OperationState.PREPARING_DISKS, OperationState.FAILED_PERMANENT, OperationState.CANCELLING),
        OperationState.FETCHING to setOf(OperationState.VERIFYING, OperationState.FAILED_RETRYABLE, OperationState.CANCELLING),
        OperationState.VERIFYING to setOf(OperationState.PREPARING_DISKS, OperationState.FAILED_PERMANENT, OperationState.CANCELLING),
        OperationState.PREPARING_DISKS to setOf(OperationState.PREPARING_BOOT, OperationState.FAILED_RETRYABLE, OperationState.CANCELLING),
        OperationState.PREPARING_BOOT to setOf(OperationState.STARTING_QEMU, OperationState.SUCCEEDED, OperationState.FAILED_RETRYABLE, OperationState.CANCELLING),
        OperationState.STARTING_QEMU to setOf(OperationState.WAITING_FOR_QMP, OperationState.FAILED_RETRYABLE, OperationState.CANCELLING),
        OperationState.WAITING_FOR_QMP to setOf(OperationState.BOOTSTRAPPING_GUEST, OperationState.FAILED_RETRYABLE, OperationState.CANCELLING),
        OperationState.BOOTSTRAPPING_GUEST to setOf(OperationState.WAITING_FOR_SSH, OperationState.FAILED_RETRYABLE, OperationState.CANCELLING),
        OperationState.WAITING_FOR_SSH to setOf(OperationState.WAITING_FOR_GUEST_MESH, OperationState.SUCCEEDED, OperationState.FAILED_RETRYABLE, OperationState.CANCELLING),
        OperationState.WAITING_FOR_GUEST_MESH to setOf(OperationState.SUCCEEDED, OperationState.FAILED_RETRYABLE, OperationState.CANCELLING),
        OperationState.FAILED_RETRYABLE to setOf(OperationState.PREFLIGHT, OperationState.ROLLING_BACK, OperationState.CANCELLING),
        OperationState.CANCELLING to setOf(OperationState.CANCELLED, OperationState.ROLLING_BACK),
        OperationState.ROLLING_BACK to setOf(OperationState.ROLLED_BACK, OperationState.FAILED_PERMANENT),
    )
    fun requireAllowed(from: OperationState, to: OperationState) {
        require(to in allowed.getOrDefault(from, emptySet())) { "invalid operation transition: $from -> $to" }
    }
}
