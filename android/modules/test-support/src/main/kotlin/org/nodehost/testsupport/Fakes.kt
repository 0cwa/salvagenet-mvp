package org.nodehost.testsupport

import java.util.concurrent.ConcurrentHashMap
import org.nodehost.core.Clock
import org.nodehost.core.OperationContext
import org.nodehost.core.RuntimeBackend
import org.nodehost.core.RuntimeStep
import org.nodehost.core.StepOutcome
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation

class FakeClock(var now: Long = 0) : Clock {
    override fun epochMillis(): Long = now
    fun advance(millis: Long) { require(millis >= 0); now += millis }
}

/** External runtime state survives replacement of FakeRuntimeBackend, modelling app process death. */
class FakeRuntimeState(
    @Volatile var observation: RuntimeObservation = RuntimeObservation.Absent(RuntimeId.DEFAULT),
) {
    internal val completedEffects = ConcurrentHashMap<String, StepOutcome>()
}

enum class FakeFailurePoint { NONE, BEFORE_EFFECT, AFTER_EFFECT_UNKNOWN_OUTCOME }

class FakeRuntimeBackend(
    val externalState: FakeRuntimeState = FakeRuntimeState(),
) : RuntimeBackend {
    val executed = mutableListOf<Pair<OperationContext, RuntimeStep>>()
    var failStepId: String? = null
    var failurePoint: FakeFailurePoint = FakeFailurePoint.NONE

    var observation: RuntimeObservation
        get() = externalState.observation
        set(value) { externalState.observation = value }

    override suspend fun observe(id: RuntimeId): RuntimeObservation = externalState.observation

    override suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome {
        val effectId = "${context.operationId.value}:${context.stepId}:${context.attempt}"
        externalState.completedEffects[effectId]?.let { return it }
        if (step.id == failStepId && failurePoint == FakeFailurePoint.BEFORE_EFFECT) {
            error("injected failure before effect: ${step.id}")
        }
        synchronized(executed) {
            require(executed.size < MAX_RECORDED_EFFECTS) { "fake effect record limit exceeded" }
            executed += context to step
        }
        applyStep(step)
        val outcome = StepOutcome(changed = true, observationHint = externalState.observation.javaClass.simpleName)
        externalState.completedEffects[effectId] = outcome
        if (step.id == failStepId && failurePoint == FakeFailurePoint.AFTER_EFFECT_UNKNOWN_OUTCOME) {
            error("injected process death after effect: ${step.id}")
        }
        return outcome
    }

    private fun applyStep(step: RuntimeStep) {
        val id = externalState.observation.id
        externalState.observation = when (step) {
            RuntimeStep.StartProcess -> RuntimeObservation.Starting(id, PROCESS_ID)
            RuntimeStep.WaitForQmp -> RuntimeObservation.Running(id, PROCESS_ID, guestReady = false)
            RuntimeStep.WaitForGuest -> RuntimeObservation.Running(id, PROCESS_ID, guestReady = true)
            RuntimeStep.RequestShutdown, RuntimeStep.ForceStop -> RuntimeObservation.Stopped(id, null)
            RuntimeStep.RemoveSystem -> RuntimeObservation.Absent(id)
            else -> externalState.observation
        }
    }

    companion object {
        private const val PROCESS_ID = 4242L
        private const val MAX_RECORDED_EFFECTS = 1_000
    }
}
