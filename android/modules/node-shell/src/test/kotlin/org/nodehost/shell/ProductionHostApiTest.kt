package org.nodehost.shell

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.io.File
import java.net.InetAddress
import java.net.URI
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.nodehost.api.ImageImportRequest
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.Clock
import org.nodehost.model.OperationState
import org.nodehost.store.NodeHostDatabase
import org.nodehost.store.RoomOperationRepository
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class ProductionHostApiTest {
    private lateinit var database: NodeHostDatabase
    private lateinit var operations: RoomOperationRepository
    private lateinit var context: Context

    @Before fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        File(context.filesDir, "nodehost-artifacts").deleteRecursively()
        File(context.filesDir, "nodehost-imports").deleteRecursively()
        database = Room.inMemoryDatabaseBuilder(context, NodeHostDatabase::class.java).build()
        operations = RoomOperationRepository(database, object : Clock { override fun epochMillis() = 1000L })
    }

    @After fun tearDown() {
        database.close()
        File(context.filesDir, "nodehost-artifacts").deleteRecursively()
        File(context.filesDir, "nodehost-imports").deleteRecursively()
    }

    @Test fun tailnetBindValueRejectsLanAndLoopback() {
        assertEquals("100.64.0.9", TailnetBindAddress("100.64.0.9").value)
        assertTrue(runCatching { TailnetBindAddress("192.168.1.2") }.isFailure)
        assertTrue(runCatching { TailnetBindAddress("127.0.0.1") }.isFailure)
    }

    @Test fun globallyRoutablePolicyRejectsPrivateCgnatDocumentationAndUlaRanges() {
        val mutations = AndroidHostMutations(
            context, database, operations, ApplyRuntimeUseCase(operations, SecureOperationIdFactory()),
            enrolledRepositoryOrigin = { URI("https://artifacts.example.test") },
        )
        listOf("127.0.0.1", "10.0.0.1", "100.64.0.1", "192.0.2.1", "192.88.99.1", "198.51.100.1", "203.0.113.1", "fc00::1", "2001:db8::1")
            .forEach { assertFalse("expected rejected address $it", mutations.isGloballyRoutable(InetAddress.getByName(it))) }
        assertTrue(mutations.isGloballyRoutable(InetAddress.getByName("8.8.8.8")))
        assertTrue(mutations.isGloballyRoutable(InetAddress.getByName("2606:4700:4700::1111")))

        val mixedResolution = AndroidHostMutations(
            context, database, operations, ApplyRuntimeUseCase(operations, SecureOperationIdFactory()),
            enrolledRepositoryOrigin = { URI("https://artifacts.example.test") },
            addressResolver = { listOf(InetAddress.getByName("8.8.8.8"), InetAddress.getByName("127.0.0.1")) },
        )
        assertTrue(runCatching { mixedResolution.resolvePublicAddresses("artifacts.example.test") }.isFailure)
    }

    @Test fun productionQueriesAdvertiseExactlyTheThreeBackedProfiles() = runBlocking {
        val queries = AndroidHostResourceQueries(context, database, operations, StoppedMesh, { 1L })
        assertEquals(
            listOf("alpine-direct-qualification", "ubuntu-2404-arm64-uefi", "k3s-worker-lab"),
            queries.profiles().map { it.id },
        )
    }

    @Test fun publicGuestBootstrapArtifactIsStrictAndCarriesSeparateOneUseKey() {
        val parsed = GuestBootstrapSecretJson.parse(guestSecret())
        assertEquals("guest-one-use-key-0001", parsed.mesh.oneUseAuthKey.value)
        assertEquals("nodeadmin", parsed.sshAccess.sshUser)
        assertFalse(parsed.raw.toString(Charsets.UTF_8).contains("host-one-use"))
        val withUnknownField = JSONObject(guestSecret().toString(Charsets.UTF_8)).put("unknown", true).toString().toByteArray()
        assertTrue(runCatching { GuestBootstrapSecretJson.parse(withUnknownField) }.isFailure)
    }

    @Test fun crashArtifactsAreRemovedWithoutDeletingPublishedPayload() {
        val mutations = AndroidHostMutations(
            context, database, operations, ApplyRuntimeUseCase(operations, SecureOperationIdFactory()),
            enrolledRepositoryOrigin = { URI("https://artifacts.example.test") },
        )
        val root = File(context.filesDir, "nodehost-artifacts").apply { deleteRecursively(); mkdirs() }
        val digest = "a".repeat(64)
        val published = File(root, "versions/image/$digest/payload").apply { parentFile!!.mkdirs(); writeText("published") }
        File(root, "image.manifest.json").writeText(JSONObject().put("version", 1).put("sha256", digest).put("sizeBytes", published.length()).put("relativePath", "versions/image/$digest/payload").toString())
        val orphan = File(root, "versions/orphan/${"b".repeat(64)}/payload").apply { parentFile!!.mkdirs(); writeText("orphan") }
        val partial = File(root, ".image.1.part").apply { writeText("partial") }

        mutations.cleanupInterruptedPublications()

        assertTrue(published.isFile)
        assertFalse(orphan.exists())
        assertFalse(partial.exists())
    }

    @Test fun failedPrivateAddressImportIsJournaledAndReplayedWithoutSecondEffect() = runBlocking {
        val mutations = AndroidHostMutations(
            context, database, operations,
            ApplyRuntimeUseCase(operations, SecureOperationIdFactory()),
            enrolledRepositoryOrigin = { URI("https://127.0.0.1") },
        )
        val request = ImageImportRequest("https://127.0.0.1/ubuntu-2404-arm64-cloud", "a".repeat(64), 1)
        val canonical = "private-address-import".toByteArray()
        assertTrue(runCatching { mutations.importImage(request, "image-import-key-0001", canonical) }.isFailure)
        val journaled = database.dao().operationByKey("image-import-key-0001")
        assertNotNull(journaled)
        assertEquals(OperationState.FAILED_RETRYABLE.name, journaled!!.state)
        val replay = mutations.importImage(request, "image-import-key-0001", canonical)
        assertEquals(OperationState.FAILED_RETRYABLE, replay.state)
    }

    @Test fun controllerRevocationIsDurableAndAuthenticatorFailsClosed() = runBlocking {
        val authenticator = EnrolledControllerAuthenticator(
            org.nodehost.model.SensitiveValue("controller-capability-0001"), "controller-1",
            isRevoked = { ControllerRevocations.isRevoked(database.openHelper.readableDatabase, it) },
        )
        assertNotNull(authenticator.authorize("Bearer controller-capability-0001", "GET", "/v1/status"))
        ControllerRevocations.revoke(
            database.openHelper.writableDatabase, "controller-1", "revoke-controller-0001", "b".repeat(64), 1000L,
        )
        assertEquals(null, authenticator.authorize("Bearer controller-capability-0001", "GET", "/v1/status"))
    }

    private object StoppedMesh : org.nodehost.core.HostMesh {
        override suspend fun configure(configuration: org.nodehost.core.HostMeshConfiguration) = Unit
        override suspend fun start() = Unit
        override suspend fun stop() = Unit
        override suspend fun status() = org.nodehost.core.HostMeshStatus(org.nodehost.core.HostMeshStatus.State.STOPPED)
        override suspend fun clearIdentity() = Unit
    }

    private fun guestSecret(): ByteArray = JSONObject()
        .put("apiVersion", "nodehost.example/v1alpha1")
        .put("kind", "GuestBootstrapSecret")
        .put("binding", JSONObject().put("enrollmentId", "enroll-0001").put("issuerSpkiSha256", "a".repeat(64)))
        .put("mesh", JSONObject().put("controlUrl", "https://mesh.example.test").put("oneUseAuthKey", "guest-one-use-key-0001").put("hostname", "node-guest"))
        .put("ssh", JSONObject().put("user", "nodeadmin").put("emergencyAuthorizedKeys", JSONArray(listOf("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey nodehost-test"))))
        .put("callback", JSONObject().put("readyUrl", "http://10.0.2.2:8080/v1/bootstrap/ready").put("capability", "guest-ready-capability-0001"))
        .toString().toByteArray()
}
