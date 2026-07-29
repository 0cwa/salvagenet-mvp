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

        if (operation.blocksEffects) {
            events(ReconciliationEvent.Completed(reason, 0))
            return
        }
        val observed = withTimeout(effectTimeoutMillis) { runtime.observe(desired.id) }
        store.recordObservation(observed)
        val plan = NodePlanner.plan(desired, observed)
        var executedSteps = 0
        for (step in plan.steps) {
            // Re-read at every boundary. beginStep repeats the check transactionally with intent creation.
            if (store.load(operation.id)?.blocksEffects != false) break
            val begun = store.beginStep(operation.id, step.id) ?: break
            val intent = begun.intent
            if (intent.status == StepStatus.SUCCEEDED.name) continue
            if (begun.recovered) {
                store.failUnknownStartedStep(intent)
                events(ReconciliationEvent.Failed(reason, "UnknownStartedIntent"))
                return
            }
            // Cancellation may commit after intent creation but before the external call.
            if (store.load(operation.id)?.blocksEffects != false) break
            try {
                val outcome = withTimeout(effectTimeoutMillis) {
                    runtime.execute(OperationContext(operation.id, step.id, intent.attempt), step)
                }
                if (!store.completeStep(intent, outcome)) break
                executedSteps++
            } catch (failure: Exception) {
                val failed = store.failStep(
                    intent,
                    if (failure is kotlinx.coroutines.TimeoutCancellationException) "EFFECT_TIMEOUT" else "EFFECT_FAILED",
                )
                if (failed) throw failure
                break
            }
        }
        if (store.load(operation.id)?.blocksEffects == false) {
            val finalObservation = withTimeout(effectTimeoutMillis) { runtime.observe(desired.id) }
            store.recordObservation(finalObservation)
            // Re-read immediately before the compare-and-set terminal transition.
            if (NodePlanner.plan(desired, finalObservation).steps.isEmpty() &&
                store.load(operation.id)?.blocksEffects == false
            ) {
                store.markSucceeded(operation.id)
            }
        }
        events(ReconciliationEvent.Completed(reason, executedSteps))
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

private val org.nodehost.model.OperationRecord.blocksEffects: Boolean
    get() = state.terminal || state == OperationState.CANCELLING

enum class WakeReason { SERVICE_STARTED, DESIRED_STATE_CHANGED, RUNTIME_EVENT, RETRY }

sealed interface ReconciliationEvent {
    val reason: WakeReason
    data class Started(override val reason: WakeReason) : ReconciliationEvent
    data class Idle(override val reason: WakeReason) : ReconciliationEvent
    data class Completed(override val reason: WakeReason, val plannedSteps: Int) : ReconciliationEvent
    data class Failed(override val reason: WakeReason, val classification: String) : ReconciliationEvent
}
