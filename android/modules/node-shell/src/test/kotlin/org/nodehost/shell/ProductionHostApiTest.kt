package org.nodehost.shell

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
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
        database = Room.inMemoryDatabaseBuilder(context, NodeHostDatabase::class.java).build()
        operations = RoomOperationRepository(database, object : Clock { override fun epochMillis() = 1000L })
    }

    @After fun tearDown() { database.close() }

    @Test fun tailnetBindValueRejectsLanAndLoopback() {
        assertEquals("100.64.0.9", TailnetBindAddress("100.64.0.9").value)
        assertTrue(runCatching { TailnetBindAddress("192.168.1.2") }.isFailure)
        assertTrue(runCatching { TailnetBindAddress("127.0.0.1") }.isFailure)
    }

    @Test fun publicGuestBootstrapArtifactIsStrictAndCarriesSeparateOneUseKey() {
        val parsed = GuestBootstrapSecretJson.parse(guestSecret())
        assertEquals("guest-one-use-key-0001", parsed.mesh.oneUseAuthKey.value)
        assertEquals("nodeadmin", parsed.sshAccess.sshUser)
        assertFalse(parsed.raw.toString(Charsets.UTF_8).contains("host-one-use"))
        val withUnknownField = JSONObject(guestSecret().toString(Charsets.UTF_8)).put("unknown", true).toString().toByteArray()
        assertTrue(runCatching { GuestBootstrapSecretJson.parse(withUnknownField) }.isFailure)
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

    private fun guestSecret(): ByteArray = JSONObject()
        .put("apiVersion", "nodehost.example/v1alpha1")
        .put("kind", "GuestBootstrapSecret")
        .put("mesh", JSONObject().put("controlUrl", "https://mesh.example.test").put("oneUseAuthKey", "guest-one-use-key-0001").put("hostname", "node-guest"))
        .put("ssh", JSONObject().put("user", "nodeadmin").put("emergencyAuthorizedKeys", JSONArray(listOf("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey nodehost-test"))))
        .put("callback", JSONObject().put("readyUrl", "http://10.0.2.2:8080/v1/bootstrap/ready").put("capability", "guest-ready-capability-0001"))
        .toString().toByteArray()
}
