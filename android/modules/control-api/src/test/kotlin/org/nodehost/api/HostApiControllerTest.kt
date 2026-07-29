package org.nodehost.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.ControllerPrincipal
import org.nodehost.core.DesiredRuntimeAcceptance
import org.nodehost.core.OperationIdFactory
import org.nodehost.core.OperationRepository
import org.nodehost.model.OperationId
import org.nodehost.model.OperationRecord
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeSpec

class HostApiControllerTest {
    @Test fun authenticatorAcceptsOnlyExactBearerCapability() = runBlocking {
        val capability = "0123456789abcdef0123456789abcdef"
        val auth = MvpControllerAuthenticator(ControllerCapability(capability))
        assertNotNull(auth.authorize("Bearer $capability", "GET", "/v1/status"))
        assertNull(auth.authorize("bearer $capability", "GET", "/v1/status"))
        assertNull(auth.authorize("Bearer ${capability}x", "GET", "/v1/status"))
        assertNull(auth.authorize(null, "GET", "/v1/status"))
    }

    @Test fun capabilityNeverAppearsInWrapperString() {
        val secret = "0123456789abcdef0123456789abcdef"
        val wrapper = ControllerCapability(secret)
        assertEquals(false, wrapper.toString().contains(secret))
    }

    @Test fun applyPersistsBeforeDispatchingAcceptedOperation() = runBlocking {
        val repository = RecordingOperations()
        val events = mutableListOf<String>()
        repository.onAccepted = { events += "persist" }
        val controller = controller(repository, AcceptedOperationDispatcher { operation ->
            assertNotNull(repository.load(operation.id))
            events += "dispatch"
        })
        val raw = """{"generation":1,"desiredState":"running","profileId":"alpine","resources":{"memoryMiB":256,"vcpus":1},"dataDisk":{"sizeGiB":1,"preserveOnDelete":true}}""".toByteArray()
        val (request, canonical) = HostApiJson.parseApplyVm("default", raw)

        val operation = controller.applyVm(request, "0123456789abcdef", canonical)

        assertEquals("op-001", operation.id.value)
        assertEquals(1L, repository.accepted?.generation)
        assertEquals(256, repository.accepted?.memoryMiB)
        assertEquals(listOf("persist", "dispatch"), events)
    }

    @Test fun removeAndCancelDispatchOnlyAfterMutationReturns() = runBlocking {
        val events = mutableListOf<String>()
        val mutations = RecordingMutations(events)
        val controller = controller(
            RecordingOperations(),
            AcceptedOperationDispatcher { events += "dispatch:${it.id.value}" },
            mutations,
        )

        controller.removeVm("default", "0123456789abcdef", "remove:default".toByteArray())
        controller.cancelOperation("op-target", "fedcba9876543210", "cancel:op-target".toByteArray())

        assertEquals(
            listOf("persist:op-remove", "dispatch:op-remove", "persist:op-cancel", "dispatch:op-cancel"),
            events,
        )
    }

    @Test fun singletonRuntimeIsRejectedSequentiallyAtEveryControllerBoundary() = runBlocking {
        val repository = RecordingOperations()
        val controller = controller(repository)
        val raw = """{"generation":1,"desiredState":"running","profileId":"alpine","resources":{"memoryMiB":256,"vcpus":1},"dataDisk":{"sizeGiB":1,"preserveOnDelete":true}}""".toByteArray()
        val (otherRequest, canonical) = HostApiJson.parseApplyVm("other", raw)

        assertThrows(IllegalArgumentException::class.java) { runBlocking { controller.vm("other") } }
        assertThrows(IllegalArgumentException::class.java) { runBlocking { controller.applyVm(otherRequest, "0123456789abcdef", canonical) } }
        assertThrows(IllegalArgumentException::class.java) { runBlocking { controller.removeVm("other", "0123456789abcdef", byteArrayOf(1)) } }
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { controller.openRecovery("other", ControllerPrincipal("controller", setOf("admin"))) }
        }
        assertNull(repository.accepted)
    }

    @Test fun durableFacingVmProjectionRejectsNonDefaultRuntime() {
        assertThrows(IllegalArgumentException::class.java) {
            HostVm("other", 1, "running", "alpine", 256, 1, 1)
        }
    }

    @Test fun concurrentNonDefaultAppliesNeverReachDurableAcceptance() = runBlocking {
        val repository = RecordingOperations()
        val controller = controller(repository)
        val raw = """{"generation":1,"desiredState":"running","profileId":"alpine","resources":{"memoryMiB":256,"vcpus":1},"dataDisk":{"sizeGiB":1,"preserveOnDelete":true}}""".toByteArray()

        val results = (1..32).map { index ->
            async(Dispatchers.Default) {
                val (request, canonical) = HostApiJson.parseApplyVm("other-$index", raw)
                runCatching { controller.applyVm(request, "idempotency-key-$index".padEnd(16, '0'), canonical) }
            }
        }.awaitAll()

        assertTrue(results.all { it.isFailure })
        assertNull(repository.accepted)
    }

    @Test fun recoveryAdmissionIsSingleSessionAndRateLimited() = runBlocking {
        var now = 0L
        val recovery = RecordingRecovery()
        val controller = controller(
            RecordingOperations(),
            recovery = recovery,
            monotonicNanos = { now },
            recoveryMaxStartsPerMinute = 2,
        )
        val principal = ControllerPrincipal("controller", setOf("admin"))
        val first = controller.openRecovery("default", principal)
        assertThrows(HostApiConflictException::class.java) {
            runBlocking { controller.openRecovery("default", principal) }
        }
        first.close()
        controller.openRecovery("default", principal).close()
        assertThrows(HostApiRateLimitException::class.java) {
            runBlocking { controller.openRecovery("default", principal) }
        }
        now = 60_000_000_001L
        controller.openRecovery("default", principal).close()
        assertEquals(3, recovery.openCount)
    }

    @Test fun recoveryByteBudgetRejectsExcess() {
        val budget = RecoveryByteBudget(5)
        budget.consume(3)
        budget.consume(2)
        assertThrows(IllegalArgumentException::class.java) { budget.consume(1) }
    }

    @Test fun applyRejectsUnknownFieldsBeforeDelegation() {
        val raw = """{"generation":1,"desiredState":"running","profileId":"alpine","resources":{"memoryMiB":256,"vcpus":1},"dataDisk":{"sizeGiB":1,"preserveOnDelete":true},"argv":[]}""".toByteArray()
        assertThrows(IllegalArgumentException::class.java) {
            HostApiJson.parseApplyVm("default", raw)
        }
    }

    @Test fun imageImportRequiresHttpsAndBoundedExpectedSize() = runBlocking {
        val controller = controller(RecordingOperations())
        val request = ImageImportRequest("http://example.invalid/image", "a".repeat(64), 1)
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { controller.importImage(request, "0123456789abcdef", byteArrayOf(1)) }
        }
        Unit
    }

    @Test fun rejectsUnsafeLanAndWildcardBindAddresses() {
        assertThrows(IllegalArgumentException::class.java) { HostControlServer.requireSafeBindAddress("0.0.0.0") }
        assertThrows(IllegalArgumentException::class.java) { HostControlServer.requireSafeBindAddress("192.168.1.2") }
        HostControlServer.requireSafeBindAddress("127.0.0.1")
        HostControlServer.requireSafeBindAddress("100.64.0.2")
    }

    private fun controller(
        repository: RecordingOperations,
        dispatcher: AcceptedOperationDispatcher = AcceptedOperationDispatcher.UNCONFIGURED,
        mutations: HostMutationUseCases = EmptyMutations,
        recovery: RecoverySshGateway = EmptyRecovery,
        monotonicNanos: () -> Long = System::nanoTime,
        recoveryMaxStartsPerMinute: Int = HostApiController.RECOVERY_MAX_STARTS_PER_MINUTE,
    ): HostApiController = HostApiController(
        authenticator = MvpControllerAuthenticator(ControllerCapability("0123456789abcdef0123456789abcdef")),
        queries = EmptyQueries,
        mutations = mutations,
        applyRuntime = ApplyRuntimeUseCase(repository, OperationIdFactory { OperationId("op-001") }),
        recoverySsh = recovery,
        acceptedOperationDispatcher = dispatcher,
        monotonicNanos = monotonicNanos,
        recoveryMaxStartsPerMinute = recoveryMaxStartsPerMinute,
    )
}

private class RecordingOperations : OperationRepository {
    @Volatile var accepted: RuntimeSpec? = null
    @Volatile private var stored: OperationRecord? = null
    var onAccepted: () -> Unit = {}
    override suspend fun load(id: OperationId): OperationRecord? = stored?.takeIf { it.id == id }
    override suspend fun save(record: OperationRecord) { stored = record }
    override suspend fun loadDesiredRuntime(id: RuntimeId): RuntimeSpec? = accepted?.takeIf { it.id == id }
    override suspend fun acceptDesiredRuntime(spec: RuntimeSpec, operation: OperationRecord): DesiredRuntimeAcceptance {
        accepted = spec
        stored = operation
        onAccepted()
        return DesiredRuntimeAcceptance.Accepted
    }
}

private object EmptyQueries : HostResourceQueries {
    override suspend fun status() = HostStatus("device", "RUNNING", "STOPPED")
    override suspend fun capabilities() = emptyList<HostCapability>()
    override suspend fun profiles() = emptyList<HostProfile>()
    override suspend fun images() = emptyList<HostImage>()
    override suspend fun vms() = emptyList<HostVm>()
    override suspend fun vm(id: RuntimeId): HostVm? = null
    override suspend fun operations() = emptyList<OperationRecord>()
    override suspend fun operation(id: String): OperationRecord? = null
    override suspend fun diagnostics() = HostDiagnostics(0, emptyMap())
}

private object EmptyMutations : HostMutationUseCases {
    override suspend fun importImage(request: ImageImportRequest, idempotencyKey: String, canonicalRequest: ByteArray) = error("unused")
    override suspend fun removeVm(id: RuntimeId, idempotencyKey: String, canonicalRequest: ByteArray) = error("unused")
    override suspend fun cancelOperation(id: String, idempotencyKey: String, canonicalRequest: ByteArray) = error("unused")
    override suspend fun revokeController(id: String, idempotencyKey: String, canonicalRequest: ByteArray) = Unit
}

private object EmptyRecovery : RecoverySshGateway {
    override suspend fun open(vmId: RuntimeId, principal: ControllerPrincipal): RecoverySshSession = error("unused")
}

private class RecordingMutations(private val events: MutableList<String>) : HostMutationUseCases {
    override suspend fun importImage(request: ImageImportRequest, idempotencyKey: String, canonicalRequest: ByteArray) = error("unused")
    override suspend fun removeVm(id: RuntimeId, idempotencyKey: String, canonicalRequest: ByteArray) =
        operation("op-remove").also { events += "persist:${it.id.value}" }
    override suspend fun cancelOperation(id: String, idempotencyKey: String, canonicalRequest: ByteArray) =
        operation("op-cancel").also { events += "persist:${it.id.value}" }
    override suspend fun revokeController(id: String, idempotencyKey: String, canonicalRequest: ByteArray) = Unit
}

private class RecordingRecovery : RecoverySshGateway {
    var openCount = 0
    override suspend fun open(vmId: RuntimeId, principal: ControllerPrincipal): RecoverySshSession {
        openCount++
        return object : RecoverySshSession {
            override suspend fun read(maxBytes: Int): ByteArray? = null
            override suspend fun write(bytes: ByteArray) = Unit
            override suspend fun close() = Unit
        }
    }
}

private fun operation(id: String) = OperationRecord(
    OperationId(id),
    "idempotency-key-001",
    "a".repeat(64),
    RuntimeId.DEFAULT,
    1,
    org.nodehost.model.OperationState.ACCEPTED,
    null,
)
