package org.nodehost.shell

import java.io.Closeable
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout
import org.nodehost.core.NodePlanner
import org.nodehost.core.OperationContext
import org.nodehost.core.RuntimeBackend
import org.nodehost.model.OperationState
import org.nodehost.model.RuntimeId
import org.nodehost.store.RoomOperationRepository
import org.nodehost.store.StepStatus

/** The only owner of RuntimeBackend mutations. Its conflated mailbox has a fixed capacity of one. */
class ReconciliationActor(
    scope: CoroutineScope,
    private val store: RoomOperationRepository,
    private val runtime: RuntimeBackend,
    private val effectTimeoutMillis: Long = DEFAULT_EFFECT_TIMEOUT_MILLIS,
    private val events: (ReconciliationEvent) -> Unit = {},
) : Closeable {
    private val wakes = Channel<WakeReason>(Channel.CONFLATED)
    private val actorJob: Job = scope.launch {
        for (reason in wakes) {
            try {
                reconcile(reason)
            } catch (failure: Exception) {
                events(ReconciliationEvent.Failed(reason, failure.javaClass.simpleName))
            }
        }
    }

    /** Never blocks a lifecycle or command caller; duplicate wakes are deliberately coalesced. */
    fun wake(reason: WakeReason): Boolean = wakes.trySend(reason).isSuccess

    private suspend fun reconcile(reason: WakeReason) {
        events(ReconciliationEvent.Started(reason))
        val desired = store.loadDesiredRuntime(RuntimeId.DEFAULT)
        if (desired == null) {
            events(ReconciliationEvent.Idle(reason))
            return
        }
        val operation = store.operationForDesired(desired)
        if (operation == null) {
            events(ReconciliationEvent.Failed(reason, "MissingOperation"))
            return
        }

        val observed = withTimeout(effectTimeoutMillis) { runtime.observe(desired.id) }
        store.recordObservation(observed)
        val plan = NodePlanner.plan(desired, observed)
        val repeatCompleted = operation.state.terminal
        for (step in plan.steps) {
            val intent = store.beginStep(operation, step.id, repeatCompleted)
            if (intent.status == StepStatus.SUCCEEDED.name) continue
            try {
                val outcome = withTimeout(effectTimeoutMillis) {
                    runtime.execute(OperationContext(operation.id, step.id, intent.attempt), step)
                }
                store.completeStep(intent, outcome)
            } catch (failure: Exception) {
                store.failStep(intent, if (failure is kotlinx.coroutines.TimeoutCancellationException) "EFFECT_TIMEOUT" else "EFFECT_FAILED")
                throw failure
            }
        }
        val finalObservation = withTimeout(effectTimeoutMillis) { runtime.observe(desired.id) }
        store.recordObservation(finalObservation)
        if (NodePlanner.plan(desired, finalObservation).steps.isEmpty()) {
            store.markSucceeded(operation)
        }
        events(ReconciliationEvent.Completed(reason, plan.steps.size))
    }

    suspend fun stop() {
        wakes.close()
        actorJob.join()
    }

    override fun close() {
        wakes.close()
    }

    companion object {
        const val DEFAULT_EFFECT_TIMEOUT_MILLIS = 30_000L
    }
}

enum class WakeReason { SERVICE_STARTED, DESIRED_STATE_CHANGED, RUNTIME_EVENT, RETRY }

sealed interface ReconciliationEvent {
    val reason: WakeReason
    data class Started(override val reason: WakeReason) : ReconciliationEvent
    data class Idle(override val reason: WakeReason) : ReconciliationEvent
    data class Completed(override val reason: WakeReason, val plannedSteps: Int) : ReconciliationEvent
    data class Failed(override val reason: WakeReason, val classification: String) : ReconciliationEvent
}
