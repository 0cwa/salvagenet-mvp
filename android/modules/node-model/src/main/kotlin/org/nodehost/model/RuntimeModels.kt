package org.nodehost.model

private val resourceIdPattern = Regex("[a-z0-9][a-z0-9-]{0,62}")

@JvmInline
value class RuntimeId(val value: String) {
    init { require(resourceIdPattern.matches(value)) { "invalid runtime id" } }

    companion object { val DEFAULT = RuntimeId("default") }
}

@JvmInline
value class VmProfileId(val value: String) {
    init { require(Regex("[a-z0-9][a-z0-9-]{0,63}").matches(value)) { "invalid profile id" } }
}

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
        require(generation >= 1) { "generation must be positive" }
        require(memoryMiB in 256..16384) { "memoryMiB is out of range" }
        require(vcpus in 1..16) { "vcpus is out of range" }
        require(dataDiskGiB in 1..1024) { "dataDiskGiB is out of range" }
    }
}

enum class GenerationDecision { INITIAL, ADVANCE, REPLAY, STALE, CONFLICT }

object RuntimeGenerationRules {
    fun decide(current: RuntimeSpec?, proposed: RuntimeSpec): GenerationDecision = when {
        current == null -> GenerationDecision.INITIAL
        proposed.generation < current.generation -> GenerationDecision.STALE
        proposed.generation > current.generation -> GenerationDecision.ADVANCE
        proposed == current -> GenerationDecision.REPLAY
        else -> GenerationDecision.CONFLICT
    }
}

sealed interface RuntimeObservation {
    val id: RuntimeId
    data class Absent(override val id: RuntimeId) : RuntimeObservation
    data class Stopped(override val id: RuntimeId, val profileId: VmProfileId?) : RuntimeObservation
    data class Starting(override val id: RuntimeId, val processId: Long?) : RuntimeObservation
    data class Running(
        override val id: RuntimeId,
        val processId: Long?,
        val guestReady: Boolean,
        val appliedGeneration: Long? = null,
    ) : RuntimeObservation {
        init {
            require(appliedGeneration == null || appliedGeneration >= 1) {
                "appliedGeneration must be positive when known"
            }
        }
    }
    data class Stopping(
        override val id: RuntimeId,
        val processId: Long?,
        val gracefulDeadlineExceeded: Boolean,
    ) : RuntimeObservation
    data class Failed(override val id: RuntimeId, val code: String, val retryable: Boolean) : RuntimeObservation
    data class Unknown(override val id: RuntimeId, val reason: String) : RuntimeObservation
}
