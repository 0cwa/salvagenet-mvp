package org.nodehost.api

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
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

    @Test fun applyParsesStrictTypedRequestAndDelegatesAtomicAcceptance() = runBlocking {
        val repository = RecordingOperations()
        val controller = controller(repository)
        val raw = """{"generation":1,"desiredState":"running","profileId":"alpine","resources":{"memoryMiB":256,"vcpus":1},"dataDisk":{"sizeGiB":1,"preserveOnDelete":true}}""".toByteArray()
        val (request, canonical) = HostApiJson.parseApplyVm("default", raw)

        val operation = controller.applyVm(request, "0123456789abcdef", canonical)

        assertEquals("op-001", operation.id.value)
        assertEquals(1L, repository.accepted?.generation)
        assertEquals(256, repository.accepted?.memoryMiB)
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

    private fun controller(repository: RecordingOperations): HostApiController = HostApiController(
        authenticator = MvpControllerAuthenticator(ControllerCapability("0123456789abcdef0123456789abcdef")),
        queries = EmptyQueries,
        mutations = EmptyMutations,
        applyRuntime = ApplyRuntimeUseCase(repository, OperationIdFactory { OperationId("op-001") }),
        recoverySsh = EmptyRecovery,
    )
}

private class RecordingOperations : OperationRepository {
    var accepted: RuntimeSpec? = null
    override suspend fun load(id: OperationId): OperationRecord? = null
    override suspend fun save(record: OperationRecord) = Unit
    override suspend fun loadDesiredRuntime(id: RuntimeId): RuntimeSpec? = null
    override suspend fun acceptDesiredRuntime(spec: RuntimeSpec, operation: OperationRecord): DesiredRuntimeAcceptance {
        accepted = spec
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
