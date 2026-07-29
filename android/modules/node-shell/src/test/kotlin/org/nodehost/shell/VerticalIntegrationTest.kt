package org.nodehost.shell

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.json.JSONArray
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.nodehost.api.ApplyVmRequest
import org.nodehost.api.HostApiController
import org.nodehost.api.HostCapability
import org.nodehost.api.HostDiagnostics
import org.nodehost.api.HostImage
import org.nodehost.api.HostMutationUseCases
import org.nodehost.api.HostProfile
import org.nodehost.api.HostResourceQueries
import org.nodehost.api.HostStatus
import org.nodehost.api.HostVm
import org.nodehost.api.ImageImportRequest
import org.nodehost.api.RecoverySshGateway
import org.nodehost.api.RecoverySshSession
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.Clock
import org.nodehost.core.EnrollmentAcceptance
import org.nodehost.core.EnrollmentRepository
import org.nodehost.core.HostMesh
import org.nodehost.core.HostMeshConfiguration
import org.nodehost.core.HostMeshStatus
import org.nodehost.core.OperationIdFactory
import org.nodehost.model.NodeEnrollment
import org.nodehost.model.OperationId
import org.nodehost.model.OperationRecord
import org.nodehost.model.RuntimeId
import org.nodehost.model.SensitiveValue
import org.nodehost.store.NodeHostDatabase
import org.nodehost.store.RoomOperationRepository
import org.nodehost.testsupport.FakeRuntimeBackend
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class VerticalIntegrationTest {
    private lateinit var database: NodeHostDatabase
    private lateinit var operations: RoomOperationRepository
    private lateinit var scope: CoroutineScope

    @Before fun setUp() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext<Context>(), NodeHostDatabase::class.java,
        ).build()
        operations = RoomOperationRepository(database, object : Clock { override fun epochMillis() = 1_000L })
        scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    }

    @After fun tearDown() { scope.cancel(); database.close() }

    @Test fun enrollmentToUbuntuRuntimeAndSeparateGuestBootstrapIsEndToEnd() = runBlocking {
        val runtime = FakeRuntimeBackend()
        var completed = CompletableDeferred<Unit>()
        val actor = ReconciliationActor(scope, operations, runtime, events = {
            if (it is ReconciliationEvent.Completed) completed.complete(Unit)
        })
        val mesh = RecordingMesh()
        val bootstrap = RecordingBootstrapStore()
        val ids = AtomicInteger()
        val installer = EnrollmentInstaller(
            InMemoryEnrollmentRepository(), operations, mesh, bootstrap,
            wakeReconciler = { actor.wake(WakeReason.DESIRED_STATE_CHANGED) },
            clock = object : Clock { override fun epochMillis() = 1_000L },
            operationIds = OperationIdFactory { OperationId("op-${ids.incrementAndGet().toString().padStart(3, '0')}") },
            materializer = GuestBootstrapMaterializer(
                tokenFactory = { "b".repeat(43) },
                callbackCapabilityFactory = { SensitiveValue("c".repeat(43)) },
            ),
        )
        val raw = enrollmentJson()
        val installed = installer.install(
            raw,
            GuestMeshBootstrap("https://mesh.example.test", SensitiveValue("guest-auth-key-distinct-0001"), "node-01-guest"),
            "enrollment-key-0001",
        )
        withTimeout(5_000) { completed.await() }
        completed = CompletableDeferred()
        val controller = HostApiController(
            installed.controllerAuthenticator,
            EmptyQueries,
            UnsupportedMutations,
            ApplyRuntimeUseCase(operations, OperationIdFactory { OperationId("op-controller-apply") }),
            LoopbackRecoverySshGateway(),
        )
        assertNotNull(controller.authorize("Bearer controller-capability-000001", "PUT", "/v1/vms/default"))
        controller.applyVm(
            ApplyVmRequest("default", 2, "running", "ubuntu-2404-arm64-uefi", 1024, 2, 8, true),
            "controller-apply-0001", "controller-generation-2".toByteArray(),
        )
        actor.wake(WakeReason.DESIRED_STATE_CHANGED)
        withTimeout(5_000) { completed.await() }

        assertEquals("host-auth-key-00000001", mesh.configuration?.oneUseAuthKey?.value)
        assertTrue(mesh.started)
        assertEquals("ubuntu-2404-arm64-uefi", operations.loadDesiredRuntime(RuntimeId.DEFAULT)?.profileId?.value)
        assertTrue(runtime.executed.any { it.second.id == "qemu.start_process" })
        assertEquals(1, runtime.executed.count { it.second.id == "qemu.start_process" })
        assertEquals("controller-1", installed.controllerAuthenticator.authorize("Bearer controller-capability-000001", "PUT", "/v1/vms/default")?.id)
        assertNull(installed.controllerAuthenticator.authorize("Bearer wrong-controller-capability", "PUT", "/v1/vms/default"))

        val materialized = checkNotNull(bootstrap.materialized)
        assertTrue(materialized.profile.userData.contains("PasswordAuthentication no"))
        assertTrue(materialized.profile.userData.contains("lock_passwd: true"))
        assertFalse(materialized.profile.userData.contains("password:"))
        val redemptions = (1..20).map { async(Dispatchers.Default) { materialized.secret.redeem(materialized.profile.token) } }.awaitAll()
        assertEquals(1, redemptions.count { it != null })
        val secret = checkNotNull(redemptions.single { it != null })
        val secretJson = JSONObject(String(secret))
        assertEquals("guest-auth-key-distinct-0001", secretJson.getJSONObject("mesh").getString("oneUseAuthKey"))
        assertEquals("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey nodehost-test", secretJson.getJSONObject("ssh").getJSONArray("emergencyAuthorizedKeys").getString(0))
        assertNull(materialized.secret.redeem(materialized.profile.token))

        // Controller transport disappearing is only absence of another wake; durable purpose remains RUNNING.
        assertEquals("RUNNING", operations.loadDesiredRuntime(RuntimeId.DEFAULT)?.desiredState?.name)
        actor.close()
    }

    @Test fun recoverySshWorksIndependentlyOfGuestMeshAndEnforcesSingleSession() = runBlocking {
        val server = ServerSocket(0, 1, java.net.InetAddress.getLoopbackAddress())
        val echoed = byteArrayOf(0x53, 0x53, 0x48)
        val serverThread = Thread {
            server.accept().use { socket ->
                val input = ByteArray(3)
                socket.getInputStream().read(input)
                socket.getOutputStream().write(echoed)
            }
        }.apply { start() }
        val gateway = LoopbackRecoverySshGateway(server.localPort)
        val principal = org.nodehost.core.ControllerPrincipal("controller-1", setOf("admin"))
        val session = gateway.open(RuntimeId.DEFAULT, principal)
        val duplicate = runCatching { gateway.open(RuntimeId.DEFAULT, principal) }
        assertTrue(duplicate.isFailure)
        session.write(byteArrayOf(1, 2, 3))
        assertArrayEquals(echoed, session.read(3))
        session.close()
        serverThread.join(2_000)
        server.close()
    }

    private fun enrollmentJson(): ByteArray = JSONObject()
        .put("apiVersion", "nodehost.example/v1alpha1").put("kind", "NodeEnrollment")
        .put("metadata", JSONObject().put("enrollmentId", "enroll-0001").put("nodeName", "node-01").put("expiresAt", "2099-01-01T00:00:00Z"))
        .put("controller", JSONObject().put("endpoint", "https://controller.example.test").put("spkiSha256", "a".repeat(64)).put("oneTimeEnrollmentToken", "controller-enrollment-0001"))
        .put("hostMesh", JSONObject().put("controlUrl", "https://mesh.example.test").put("oneUseAuthKey", "host-auth-key-00000001").put("hostname", "node-01").put("expectedTags", JSONArray(listOf("tag:nodehost"))))
        .put("hostAccess", JSONObject().put("controllerCapability", "controller-capability-000001").put("allowedControllerId", "controller-1"))
        .put("guestAccess", JSONObject().put("sshUser", "nodeadmin").put("emergencyAuthorizedKeys", JSONArray(listOf("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey nodehost-test"))))
        .put("artifacts", JSONObject().put("repositoryUrl", "https://artifacts.example.test").put("profileIds", JSONArray(listOf("ubuntu-2404-arm64-uefi"))))
        .put("initialRuntime", JSONObject().put("profileId", "ubuntu-2404-arm64-uefi").put("desiredState", "stopped").put("memoryMiB", 1024).put("vcpus", 2).put("dataDiskGiB", 8))
        .toString().toByteArray()

    private object EmptyQueries : HostResourceQueries {
        override suspend fun status() = HostStatus("device-test", "running", "running")
        override suspend fun capabilities() = emptyList<HostCapability>()
        override suspend fun profiles() = emptyList<HostProfile>()
        override suspend fun images() = emptyList<HostImage>()
        override suspend fun vms() = emptyList<HostVm>()
        override suspend fun vm(id: RuntimeId): HostVm? = null
        override suspend fun operations() = emptyList<OperationRecord>()
        override suspend fun operation(id: String): OperationRecord? = null
        override suspend fun diagnostics() = HostDiagnostics(1, emptyMap())
    }

    private object UnsupportedMutations : HostMutationUseCases {
        override suspend fun importImage(request: ImageImportRequest, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord = error("not used")
        override suspend fun removeVm(id: RuntimeId, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord = error("not used")
        override suspend fun cancelOperation(id: String, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord = error("not used")
        override suspend fun revokeController(id: String, idempotencyKey: String, canonicalRequest: ByteArray) = error("not used")
    }

    private class RecordingBootstrapStore : GuestBootstrapStore {
        var materialized: MaterializedGuestBootstrap? = null
        override suspend fun save(materialized: MaterializedGuestBootstrap) { this.materialized = materialized }
    }

    private class RecordingMesh : HostMesh {
        var configuration: HostMeshConfiguration? = null
        var started = false
        override suspend fun configure(configuration: HostMeshConfiguration) { this.configuration = configuration }
        override suspend fun start() { started = true }
        override suspend fun stop() { started = false }
        override suspend fun status() = HostMeshStatus(if (started) HostMeshStatus.State.RUNNING else HostMeshStatus.State.STOPPED)
        override suspend fun clearIdentity() { started = false; configuration = null }
    }

    private class InMemoryEnrollmentRepository : EnrollmentRepository {
        var installed: Pair<NodeEnrollment, OperationRecord>? = null
        override suspend fun load() = installed?.first
        override suspend fun acceptEnrollment(enrollment: NodeEnrollment, operation: OperationRecord): EnrollmentAcceptance {
            if (installed != null) return EnrollmentAcceptance.Replay(installed!!.second)
            installed = enrollment to operation
            return EnrollmentAcceptance.Accepted
        }
    }
}
