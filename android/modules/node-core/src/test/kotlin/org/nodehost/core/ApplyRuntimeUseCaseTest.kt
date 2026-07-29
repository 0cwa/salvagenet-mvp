package org.nodehost.core

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertThrows
import org.junit.Test
import org.nodehost.model.*

class ApplyRuntimeUseCaseTest {
    private val spec = RuntimeSpec(
        generation = 1,
        desiredState = DesiredRuntimeState.RUNNING,
        profileId = VmProfileId("ubuntu-2404-arm64-uefi"),
        memoryMiB = 1024,
        vcpus = 2,
        dataDiskGiB = 8,
    )

    @Test
    fun desiredStateAndOperationAreAcceptedTogether() = runBlocking {
        val repository = InMemoryOperationRepository()
        val operation = ApplyRuntimeUseCase(repository) { OperationId("op-001") }
            .apply(spec, "idempotency-key-0001", "request".toByteArray())

        assertEquals(spec, repository.desired)
        assertSame(operation, repository.operations.single())
        assertEquals(1, repository.atomicAcceptCount)
    }

    @Test
    fun replayReturnsOriginalOperation() = runBlocking {
        val repository = InMemoryOperationRepository()
        var sequence = 0
        val useCase = ApplyRuntimeUseCase(repository) { OperationId("op-${++sequence}00") }
        val first = useCase.apply(spec, "idempotency-key-0001", "request".toByteArray())
        val replay = useCase.apply(spec, "idempotency-key-0001", "request".toByteArray())

        assertSame(first, replay)
        assertEquals(1, repository.operations.size)
    }

    @Test
    fun concurrentDuplicatesCommitExactlyOnce() = runBlocking {
        val repository = InMemoryOperationRepository()
        var sequence = 0
        val useCase = ApplyRuntimeUseCase(repository) {
            synchronized(repository) { OperationId("op-${++sequence}00") }
        }

        val results = List(20) {
            async(Dispatchers.Default) {
                useCase.apply(spec, "idempotency-key-0001", "request".toByteArray())
            }
        }.awaitAll()

        assertEquals(1, results.map { it.id }.distinct().size)
        assertEquals(1, repository.operations.size)
    }

    @Test
    fun conflictingReplayIsRejected() {
        val repository = InMemoryOperationRepository()
        val useCase = ApplyRuntimeUseCase(repository) { OperationId("op-001") }
        runBlocking { useCase.apply(spec, "idempotency-key-0001", "request-a".toByteArray()) }

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { useCase.apply(spec, "idempotency-key-0001", "request-b".toByteArray()) }
        }
    }

    @Test
    fun staleAndSameGenerationChangesAreRejected() {
        val repository = InMemoryOperationRepository()
        var sequence = 0
        val useCase = ApplyRuntimeUseCase(repository) { OperationId("op-${++sequence}00") }
        runBlocking {
            useCase.apply(spec.copy(generation = 2), "idempotency-key-0001", "request-1".toByteArray())
        }

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { useCase.apply(spec, "idempotency-key-0002", "request-2".toByteArray()) }
        }
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                useCase.apply(spec.copy(generation = 2, memoryMiB = 2048), "idempotency-key-0003", "request-3".toByteArray())
            }
        }
    }

    @Test
    fun oversizedCanonicalRequestIsRejectedBeforeRepositoryEffect() {
        val repository = InMemoryOperationRepository()
        val useCase = ApplyRuntimeUseCase(repository) { OperationId("op-001") }

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                useCase.apply(spec, "idempotency-key-0001", ByteArray(MAX_CANONICAL_REQUEST_BYTES + 1))
            }
        }
        assertEquals(0, repository.atomicAcceptCount)
    }
}

private class InMemoryOperationRepository : OperationRepository {
    var desired: RuntimeSpec? = null
    val operations = mutableListOf<OperationRecord>()
    var atomicAcceptCount: Int = 0

    override suspend fun load(id: OperationId): OperationRecord? = synchronized(this) {
        operations.find { it.id == id }
    }

    override suspend fun save(record: OperationRecord) = synchronized(this) {
        operations.replaceAll { if (it.id == record.id) record else it }
    }

    override suspend fun loadDesiredRuntime(id: RuntimeId): RuntimeSpec? = synchronized(this) {
        desired?.takeIf { it.id == id }
    }

    override suspend fun acceptDesiredRuntime(
        spec: RuntimeSpec,
        operation: OperationRecord,
    ): DesiredRuntimeAcceptance = synchronized(this) {
        atomicAcceptCount += 1
        operations.find { it.idempotencyKey == operation.idempotencyKey }?.let { existing ->
            return@synchronized if (existing.requestDigest == operation.requestDigest) {
                DesiredRuntimeAcceptance.Replay(existing)
            } else {
                DesiredRuntimeAcceptance.IdempotencyConflict
            }
        }
        val decision = RuntimeGenerationRules.decide(desired, spec)
        if (decision !in setOf(GenerationDecision.INITIAL, GenerationDecision.ADVANCE)) {
            return@synchronized DesiredRuntimeAcceptance.GenerationRejected(decision)
        }
        desired = spec
        operations += operation
        DesiredRuntimeAcceptance.Accepted
    }
}
