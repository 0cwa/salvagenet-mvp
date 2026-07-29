package org.nodehost.store

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.nodehost.core.DesiredRuntimeAcceptance
import org.nodehost.core.StepOutcome
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.OperationId
import org.nodehost.model.OperationRecord
import org.nodehost.model.OperationState
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class RoomOperationRepositoryTest {
    private lateinit var database: NodeHostDatabase
    private lateinit var repository: RoomOperationRepository
    private val clock = MutableClock(100)

    @Before
    fun setUp() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext<Context>(),
            NodeHostDatabase::class.java,
        ).build()
        repository = RoomOperationRepository(database, clock)
    }

    @After fun tearDown() = database.close()

    @Test
    fun desiredGenerationAndOperationCommitAtomicallyAndRejectStaleOrConflict() = runBlocking {
        assertTrue(repository.acceptDesiredRuntime(spec(2), operation("op-200", "key-000000000002", 2)) is DesiredRuntimeAcceptance.Accepted)
        assertTrue(repository.acceptDesiredRuntime(spec(1), operation("op-100", "key-000000000001", 1)) is DesiredRuntimeAcceptance.GenerationRejected)
        assertTrue(repository.acceptDesiredRuntime(spec(2).copy(memoryMiB = 2048), operation("op-201", "key-000000000003", 2)) is DesiredRuntimeAcceptance.GenerationRejected)
        assertEquals(2L, repository.loadDesiredRuntime(RuntimeId.DEFAULT)?.generation)
        assertNull(repository.load(OperationId("op-100")))
    }

    @Test
    fun idempotencyReplayAndConflictAreDurableAndConcurrentSafe() = runBlocking {
        val sequence = AtomicInteger()
        val results = List(16) {
            async(Dispatchers.Default) {
                repository.acceptDesiredRuntime(
                    spec(1),
                    operation("op-${100 + sequence.incrementAndGet()}", "same-key-00000001", 1),
                )
            }
        }.awaitAll()

        assertEquals(1, results.count { it is DesiredRuntimeAcceptance.Accepted })
        assertEquals(15, results.count { it is DesiredRuntimeAcceptance.Replay })
        assertTrue(
            repository.acceptDesiredRuntime(spec(2), operation("op-999", "same-key-00000001", 2, digest = "b".repeat(64))) is DesiredRuntimeAcceptance.IdempotencyConflict,
        )
    }

    @Test
    fun intentAndResultJournalBracketEffectAndStartedIntentSurvivesRestart() = runBlocking {
        val operation = operation("op-300", "key-000000000300", 1)
        repository.acceptDesiredRuntime(spec(1), operation)
        val intent = requireNotNull(repository.beginStep(operation.id, "qemu.start_process")).intent
        assertEquals(StepStatus.STARTED.name, RoomOperationRepository(database, clock).steps(operation.id).single().status)

        clock.now = 200
        RoomOperationRepository(database, clock).completeStep(intent, StepOutcome(true, "started"))
        val result = repository.steps(operation.id).single()
        assertEquals(StepStatus.SUCCEEDED.name, result.status)
        assertEquals(200L, result.finishedAtEpochMillis)
        assertEquals("started", result.resultDetail)
    }

    @Test
    fun cancellationIsAtomicPreservesDesiredAndWinsAgainstStaleSuccessOrFailure() = runBlocking {
        val operation = operation("op-400", "key-000000000400", 1)
        repository.acceptDesiredRuntime(spec(1), operation)
        val intent = requireNotNull(repository.beginStep(operation.id, "qemu.start_process")).intent

        assertEquals(
            OperationState.CANCELLED,
            repository.cancelOperation(operation.id, setOf(OperationState.ACCEPTED)).state,
        )
        assertEquals(DesiredRuntimeState.RUNNING, repository.loadDesiredRuntime(RuntimeId.DEFAULT)?.desiredState)
        assertEquals(false, repository.completeStep(intent, StepOutcome(true, "started")))
        assertEquals(false, repository.failStep(intent, "EFFECT_FAILED"))
        assertEquals(false, repository.markSucceeded(operation.id))
        assertEquals(OperationState.CANCELLED, repository.load(operation.id)?.state)
        assertEquals(StepStatus.STARTED.name, repository.steps(operation.id).single().status)
    }

    @Test
    fun systemReconciliationAttemptHasStableIdAndConcurrentWakeDeduplication() = runBlocking {
        val userOperation = operation("op-500", "key-000000000500", 1)
        repository.acceptDesiredRuntime(spec(1), userOperation)
        repository.markSucceeded(userOperation.id)

        val attempts = List(16) {
            async(Dispatchers.Default) { repository.beginSystemReconciliation(spec(1)) }
        }.awaitAll()

        assertEquals(setOf("sys-reconcile-default-1-1"), attempts.map { it?.id?.value }.toSet())
        assertEquals(OperationState.ACCEPTED, repository.operationForDesired(spec(1))?.state)
        assertEquals(DesiredRuntimeState.RUNNING, repository.loadDesiredRuntime(RuntimeId.DEFAULT)?.desiredState)
    }

    @Test
    fun systemReconciliationAttemptsAreDurablyBounded() = runBlocking {
        val userOperation = operation("op-600", "key-000000000600", 1)
        repository.acceptDesiredRuntime(spec(1), userOperation)
        repository.markSucceeded(userOperation.id)

        repeat(RoomOperationRepository.MAX_SYSTEM_RECONCILIATION_ATTEMPTS) { index ->
            val attempt = requireNotNull(repository.beginSystemReconciliation(spec(1)))
            assertEquals(index + 1, attempt.id.value.substringAfterLast('-').toInt())
            repository.markSucceeded(attempt.id)
        }

        val exhausted = requireNotNull(repository.beginSystemReconciliation(spec(1)))
        assertEquals("sys-reconcile-default-1-32", exhausted.id.value)
        assertEquals(OperationState.SUCCEEDED, exhausted.state)
    }

    @Test
    fun currentObservationIsDurableDerivedState() = runBlocking {
        repository.recordObservation(RuntimeObservation.Running(RuntimeId.DEFAULT, 42, guestReady = true))
        assertEquals(
            RuntimeObservation.Running(RuntimeId.DEFAULT, 42, guestReady = true),
            RoomOperationRepository(database, clock).current(RuntimeId.DEFAULT),
        )
        assertNull(repository.loadDesiredRuntime(RuntimeId.DEFAULT))
    }

    private fun spec(generation: Long) = RuntimeSpec(
        generation = generation,
        desiredState = DesiredRuntimeState.RUNNING,
        profileId = VmProfileId("alpine-direct"),
        memoryMiB = 512,
        vcpus = 1,
        dataDiskGiB = 4,
    )

    private fun operation(id: String, key: String, generation: Long, digest: String = "a".repeat(64)) = OperationRecord(
        OperationId(id), key, digest, RuntimeId.DEFAULT, generation, OperationState.ACCEPTED, null,
    )
}

private class MutableClock(var now: Long) : org.nodehost.core.Clock {
    override fun epochMillis(): Long = now
}
