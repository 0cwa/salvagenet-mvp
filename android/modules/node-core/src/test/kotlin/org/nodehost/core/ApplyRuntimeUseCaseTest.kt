package org.nodehost.core

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertThrows
import org.junit.Test
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.OperationId
import org.nodehost.model.OperationRecord
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId

class ApplyRuntimeUseCaseTest {
    private val spec = RuntimeSpec(
        id = RuntimeId.DEFAULT,
        generation = 1,
        desiredState = DesiredRuntimeState.RUNNING,
        profileId = VmProfileId("ubuntu-2404-arm64-uefi"),
        memoryMiB = 1024,
        vcpus = 2,
        dataDiskGiB = 8,
    )

    @Test
    fun desiredStateAndOperationAreAcceptedTogether() = runBlocking {
        val repository = RecordingOperationRepository()
        val useCase = ApplyRuntimeUseCase(repository) { OperationId("op-1") }

        val operation = useCase.apply(spec, "idempotency-key-0001", "request".toByteArray())

        assertEquals(spec, repository.desired)
        assertSame(operation, repository.operation)
        assertEquals(1, repository.atomicAcceptCount)
    }

    @Test
    fun replayReturnsOriginalOperation() = runBlocking {
        val repository = RecordingOperationRepository()
        val useCase = ApplyRuntimeUseCase(repository) { OperationId("op-1") }
        val first = useCase.apply(spec, "idempotency-key-0001", "request".toByteArray())

        val replay = useCase.apply(spec, "idempotency-key-0001", "request".toByteArray())

        assertSame(first, replay)
        assertEquals(1, repository.atomicAcceptCount)
    }

    @Test
    fun conflictingReplayIsRejected() {
        val repository = RecordingOperationRepository()
        val useCase = ApplyRuntimeUseCase(repository) { OperationId("op-1") }
        runBlocking { useCase.apply(spec, "idempotency-key-0001", "request-a".toByteArray()) }

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                useCase.apply(spec, "idempotency-key-0001", "request-b".toByteArray())
            }
        }
    }
}

private class RecordingOperationRepository : OperationRepository {
    var desired: RuntimeSpec? = null
    var operation: OperationRecord? = null
    var atomicAcceptCount: Int = 0

    override suspend fun findByIdempotencyKey(key: String): OperationRecord? =
        operation?.takeIf { it.idempotencyKey == key }

    override suspend fun load(id: OperationId): OperationRecord? =
        operation?.takeIf { it.id == id }

    override suspend fun save(record: OperationRecord) {
        operation = record
    }

    override suspend fun loadDesiredRuntime(id: RuntimeId): RuntimeSpec? =
        desired?.takeIf { it.id == id }

    override suspend fun acceptDesiredRuntime(spec: RuntimeSpec, operation: OperationRecord) {
        desired = spec
        this.operation = operation
        atomicAcceptCount += 1
    }
}
