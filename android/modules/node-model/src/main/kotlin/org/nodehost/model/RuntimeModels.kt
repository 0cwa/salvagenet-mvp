package org.nodehost.model

@JvmInline value class RuntimeId(val value: String) {
    init { require(value.matches(Regex("[a-z0-9][a-z0-9-]{0,62}"))) }
    companion object { val DEFAULT = RuntimeId("default") }
}
@JvmInline value class VmProfileId(val value: String)

enum class DesiredRuntimeState { ABSENT, STOPPED, RUNNING }

data class RuntimeSpec(
    val id: RuntimeId = RuntimeId.DEFAULT,
    val generation: Long,
    val desiredState: DesiredRuntimeState,
    val profileId: VmProfileId,
    val memoryMiB: Int,
    val vcpus: Int,
    val dataDiskGiB: Int,
    val preserveDataOnDelete: Boolean = true,
) {
    init {
        require(generation >= 0)
        require(memoryMiB in 256..16384)
        require(vcpus in 1..16)
        require(dataDiskGiB in 1..1024)
    }
}

sealed interface RuntimeObservation {
    val id: RuntimeId
    data class Absent(override val id: RuntimeId) : RuntimeObservation
    data class Stopped(override val id: RuntimeId, val profileId: VmProfileId?) : RuntimeObservation
    data class Starting(override val id: RuntimeId, val processId: Long?) : RuntimeObservation
    data class Running(override val id: RuntimeId, val processId: Long?, val guestReady: Boolean) : RuntimeObservation
    data class Stopping(
        override val id: RuntimeId,
        val processId: Long?,
        val gracefulDeadlineExceeded: Boolean,
    ) : RuntimeObservation
    data class Failed(override val id: RuntimeId, val code: String, val retryable: Boolean) : RuntimeObservation
    data class Unknown(override val id: RuntimeId, val reason: String) : RuntimeObservation
}
