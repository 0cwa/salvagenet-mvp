package org.nodehost.shell

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.nodehost.core.DesiredRuntimeAcceptance
import org.nodehost.core.OperationContext
import org.nodehost.core.RuntimeBackend
import org.nodehost.core.RuntimeStep
import org.nodehost.core.StepOutcome
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.OperationId
import org.nodehost.model.OperationRecord
import org.nodehost.model.OperationState
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId
import org.nodehost.store.NodeHostDatabase
import org.nodehost.store.RoomOperationRepository
import org.nodehost.store.StepStatus
import org.nodehost.testsupport.FakeClock
import org.nodehost.testsupport.FakeFailurePoint
import org.nodehost.testsupport.FakeRuntimeBackend
import org.nodehost.testsupport.FakeRuntimeState
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class ReconciliationActorTest {
    private lateinit var database: NodeHostDatabase
    private lateinit var store: RoomOperationRepository
    private val clock = FakeClock(1_000)
    private val scopes = mutableListOf<CoroutineScope>()

    @Before fun setUp() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext<Context>(), NodeHostDatabase::class.java,
        ).build()
        store = RoomOperationRepository(database, clock)
    }

    @After fun tearDown() {
        scopes.forEach(CoroutineScope::cancel)
        database.close()
    }

    @Test
    fun processDeathAfterEffectRecoversFromObservationWithoutRepeatingStart() = runBlocking {
        val operation = acceptDesired()
        val external = FakeRuntimeState()
        val firstRuntime = FakeRuntimeBackend(external).apply {
            failStepId = "qemu.start_process"
            failurePoint = FakeFailurePoint.AFTER_EFFECT_UNKNOWN_OUTCOME
        }
        runActor(firstRuntime, expectFailure = true)
        assertTrue(external.observation is RuntimeObservation.Starting)
        assertEquals(StepStatus.FAILED.name, store.steps(operation.id).last().status)

        val restartedRuntime = FakeRuntimeBackend(external)
        runActor(restartedRuntime)

        assertEquals(0, restartedRuntime.executed.count { it.second.id == "qemu.start_process" })
        assertEquals(RuntimeObservation.Running(RuntimeId.DEFAULT, 4242, true), external.observation)
        assertEquals(OperationState.SUCCEEDED, store.load(operation.id)?.state)
    }

    @Test
    fun failedEffectIsRetriedWithANewBoundedAttemptAndStableJournal() = runBlocking {
        val operation = acceptDesired()
        val runtime = FakeRuntimeBackend().apply {
            failStepId = "qemu.start_process"
            failurePoint = FakeFailurePoint.BEFORE_EFFECT
        }
        runActor(runtime, expectFailure = true)
        runtime.failurePoint = FakeFailurePoint.NONE
        runActor(runtime)

        val starts = store.steps(operation.id).filter { it.stepId == "qemu.start_process" }
        assertEquals(listOf(1, 2), starts.map { it.attempt })
        assertEquals(listOf(StepStatus.FAILED.name, StepStatus.SUCCEEDED.name), starts.map { it.status })
    }

    @Test
    fun taskRemovalDoesNotRedefineDurableDesiredState() = runBlocking {
        acceptDesired()
        NodeSupervisorService().onTaskRemoved(null)
        assertEquals(DesiredRuntimeState.RUNNING, store.loadDesiredRuntime(RuntimeId.DEFAULT)?.desiredState)
    }

    @Test
    fun cancelBeforeEffectPreventsExecutionAndPreservesDesiredState() = runBlocking {
        val operation = acceptDesired()
        val executions = AtomicInteger()
        val runtime = object : RuntimeBackend {
            override suspend fun observe(id: RuntimeId): RuntimeObservation {
                store.cancelOperation(operation.id, setOf(OperationState.ACCEPTED))
                return RuntimeObservation.Absent(id)
            }
            override suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome {
                executions.incrementAndGet()
                return StepOutcome(true)
            }
        }

        runActor(runtime)

        assertEquals(0, executions.get())
        assertEquals(OperationState.CANCELLED, store.load(operation.id)?.state)
        assertEquals(DesiredRuntimeState.RUNNING, store.loadDesiredRuntime(RuntimeId.DEFAULT)?.desiredState)
    }

    @Test
    fun cancelDuringEffectStopsFollowingEffectsAndCannotBeOverwritten() = runBlocking {
        val operation = acceptDesired()
        val entered = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        val executions = AtomicInteger()
        val runtime = object : RuntimeBackend {
            override suspend fun observe(id: RuntimeId) = RuntimeObservation.Absent(id)
            override suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome {
                executions.incrementAndGet()
                entered.complete(Unit)
                release.await()
                return StepOutcome(true)
            }
        }
        val completion = startActor(runtime)
        withTimeout(5_000) { entered.await() }
        store.cancelOperation(operation.id, setOf(OperationState.ACCEPTED))
        release.complete(Unit)
        withTimeout(5_000) { completion.await() }

        assertEquals(1, executions.get())
        assertEquals(OperationState.CANCELLED, store.load(operation.id)?.state)
        assertEquals(StepStatus.STARTED.name, store.steps(operation.id).single().status)
    }

    @Test
    fun cancelImmediatelyBeforeSuccessUpdateWinsCompareAndSet() = runBlocking {
        val operation = acceptDesired()
        val runtime = object : RuntimeBackend {
            override suspend fun observe(id: RuntimeId) = RuntimeObservation.Absent(id)
            override suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome {
                store.cancelOperation(operation.id, setOf(OperationState.ACCEPTED))
                return StepOutcome(true)
            }
        }

        runActor(runtime)

        assertEquals(OperationState.CANCELLED, store.load(operation.id)?.state)
        assertEquals(StepStatus.STARTED.name, store.steps(operation.id).single().status)
    }

    @Test
    fun restartAfterCancelDoesNotReplayEffects() = runBlocking {
        val operation = acceptDesired()
        store.cancelOperation(operation.id, setOf(OperationState.ACCEPTED))
        val runtime = FakeRuntimeBackend()

        runActor(runtime)

        assertTrue(runtime.executed.isEmpty())
        assertEquals(OperationState.CANCELLED, store.load(operation.id)?.state)
    }

    @Test
    fun unknownStartedIntentFailsPermanentWithoutReplayingEffect() = runBlocking {
        val operation = acceptDesired()
        store.beginStep(operation.id, "qemu.verify_profile")
        val runtime = FakeRuntimeBackend()

        runActor(runtime, expectFailure = true)

        assertTrue(runtime.executed.isEmpty())
        assertEquals(OperationState.FAILED_PERMANENT, store.load(operation.id)?.state)
        assertEquals("UNKNOWN_EFFECT_OUTCOME", store.load(operation.id)?.errorCode)
        assertEquals(StepStatus.FAILED.name, store.steps(operation.id).single().status)
    }

    @Test
    fun effectDeadlinePersistsExplicitRetryableFailure() = runBlocking {
        val operation = acceptDesired()
        val delegate = FakeRuntimeBackend()
        val blocked = object : RuntimeBackend {
            override suspend fun observe(id: RuntimeId) = delegate.observe(id)
            override suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome {
                delay(10_000)
                return delegate.execute(context, step)
            }
        }
        val finished = CompletableDeferred<ReconciliationEvent>()
        val scope = newScope()
        val actor = ReconciliationActor(scope, store, blocked, effectTimeoutMillis = 25, events = {
            if (it is ReconciliationEvent.Failed) finished.complete(it)
        })
        actor.wake(WakeReason.RETRY)
        withTimeout(5_000) { finished.await() }
        actor.close()

        assertEquals("EFFECT_TIMEOUT", store.load(operation.id)?.errorCode)
        assertEquals(StepStatus.FAILED.name, store.steps(operation.id).single().status)
    }

    @Test
    fun conflatedWakeQueueSerializesRuntimeMutations() = runBlocking {
        acceptDesired()
        val runtime = FakeRuntimeBackend()
        val events = CopyOnWriteArrayList<ReconciliationEvent>()
        val completed = CompletableDeferred<Unit>()
        val scope = newScope()
        val actor = ReconciliationActor(scope, store, runtime, events = {
            events += it
            if (it is ReconciliationEvent.Completed) completed.complete(Unit)
        })
        repeat(100) { actor.wake(WakeReason.RUNTIME_EVENT) }
        withTimeout(5_000) { completed.await() }
        actor.close()

        assertEquals(1, runtime.executed.count { it.second.id == "qemu.start_process" })
        assertTrue(events.count { it is ReconciliationEvent.Completed } <= 2)
    }

    private suspend fun acceptDesired(): OperationRecord {
        val operation = OperationRecord(
            OperationId("op-001"), "idempotency-key-0001", "a".repeat(64), RuntimeId.DEFAULT, 1,
            OperationState.ACCEPTED, null,
        )
        val accepted = store.acceptDesiredRuntime(
            RuntimeSpec(
                generation = 1,
                desiredState = DesiredRuntimeState.RUNNING,
                profileId = VmProfileId("alpine-direct"),
                memoryMiB = 512,
                vcpus = 1,
                dataDiskGiB = 4,
            ),
            operation,
        )
        assertTrue(accepted is DesiredRuntimeAcceptance.Accepted)
        return operation
    }

    private suspend fun runActor(runtime: RuntimeBackend, expectFailure: Boolean = false) {
        val finished = startActor(runtime)
        val result = withTimeout(5_000) { finished.await() }
        assertEquals(expectFailure, result is ReconciliationEvent.Failed)
    }

    private fun startActor(runtime: RuntimeBackend): CompletableDeferred<ReconciliationEvent> {
        val finished = CompletableDeferred<ReconciliationEvent>()
        val actor = ReconciliationActor(newScope(), store, runtime, events = {
            if (it is ReconciliationEvent.Completed || it is ReconciliationEvent.Failed) finished.complete(it)
        })
        actor.wake(WakeReason.SERVICE_STARTED)
        return finished
    }

    private fun newScope() = CoroutineScope(SupervisorJob() + Dispatchers.Default).also(scopes::add)
}
