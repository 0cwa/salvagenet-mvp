package org.nodehost.mesh

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.nodehost.core.HostMeshConfiguration
import org.nodehost.core.HostMeshStatus
import org.nodehost.model.SensitiveValue

class LibtailscaleHostMeshTest {
    private val configuration = HostMeshConfiguration(
        controlUrl = "https://headscale.example.test",
        hostname = "phone-node",
        oneUseAuthKey = SensitiveValue("fake-one-use-key-abcdefghijklmnop"),
    )

    @Test fun `imported typed configuration reaches adapter and encrypted store seam`() = runBlocking {
        val fixture = fixture(permission = true)

        fixture.mesh.configure(configuration)

        assertEquals(configuration, fixture.backend.configured.single())
        assertEquals(configuration.controlUrl, fixture.store.value?.controlUrl)
        assertEquals(configuration.hostname, fixture.store.value?.hostname)
        assertEquals(configuration.oneUseAuthKey.value, fixture.store.value?.oneUseAuthKey)
    }

    @Test fun `release rejects cleartext before persistence or LocalAPI`() {
        val fixture = fixture(permission = true)
        val cleartext = configuration.copy(controlUrl = "http://headscale.lab.test:8080")

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { fixture.mesh.configure(cleartext) }
        }

        assertNull(fixture.store.value)
        assertTrue(fixture.backend.configured.isEmpty())
    }

    @Test fun `debug lab policy accepts cleartext control URL`() = runBlocking {
        val fixture = fixture(permission = true, controlUrlPolicy = ControlUrlPolicy.DEBUG_LAB)
        val cleartext = configuration.copy(controlUrl = "http://headscale.lab.test:8080")

        fixture.mesh.configure(cleartext)

        assertEquals(cleartext, fixture.backend.configured.single())
        assertEquals(cleartext.controlUrl, fixture.store.value?.controlUrl)
    }

    @Test fun `restart of old cleartext state fails closed before backend start`() {
        val fixture = fixture(permission = true)
        fixture.store.value = PersistedMeshConfiguration(
            "http://old-headscale.lab.test:8080",
            configuration.hostname,
            configuration.oneUseAuthKey.value,
        )

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { fixture.mesh.start() }
        }

        assertTrue(fixture.backend.startKeys.isEmpty())
    }

    @Test fun `missing VPN approval is reported without enrollment effect`() = runBlocking {
        val fixture = fixture(permission = false)
        fixture.mesh.configure(configuration)

        fixture.mesh.start()

        assertEquals(HostMeshStatus.State.NEEDS_PERMISSION, fixture.mesh.status().state)
        assertTrue(fixture.backend.startKeys.isEmpty())
        assertEquals(configuration.oneUseAuthKey.value, fixture.store.value?.oneUseAuthKey)
    }

    @Test fun `one-use key is retained while enrolling and deleted only after running`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)
        fixture.mesh.start()

        fixture.backend.observation = BackendMeshSnapshot(BackendMeshSnapshot.State.ENROLLING)
        assertEquals(HostMeshStatus.State.ENROLLING, fixture.mesh.status().state)
        assertEquals(configuration.oneUseAuthKey.value, fixture.store.value?.oneUseAuthKey)

        fixture.backend.observation = BackendMeshSnapshot(
            BackendMeshSnapshot.State.RUNNING,
            addresses = listOf("100.64.0.8", "fd7a:115c:a1e0::8"),
        )
        val running = fixture.mesh.status()
        assertEquals(HostMeshStatus.State.RUNNING, running.state)
        assertEquals(listOf("100.64.0.8", "fd7a:115c:a1e0::8"), running.addresses)
        assertNull(fixture.store.value?.oneUseAuthKey)
    }

    @Test fun `normal restart uses persisted identity without replaying deleted key`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)
        fixture.mesh.start()
        fixture.backend.observation = BackendMeshSnapshot(BackendMeshSnapshot.State.RUNNING)
        fixture.mesh.status()
        fixture.mesh.stop()

        fixture.mesh.start()

        assertEquals(listOf(configuration.oneUseAuthKey.value, null), fixture.backend.startKeys)
    }

    @Test fun `duplicate start is replayed through idempotent LocalAPI start`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)

        fixture.mesh.start()
        fixture.mesh.start()

        assertEquals(2, fixture.backend.startKeys.size)
    }

    @Test fun `configuration failure rolls persisted plan back`() {
        val fixture = fixture(permission = true)
        fixture.backend.configureFailure = IllegalStateException("offline")

        assertThrows(IllegalStateException::class.java) {
            runBlocking { fixture.mesh.configure(configuration) }
        }

        assertNull(fixture.store.value)
    }

    @Test fun `enrollment observations are bounded and become typed failure`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)
        fixture.mesh.start()
        fixture.backend.observation = BackendMeshSnapshot(BackendMeshSnapshot.State.ENROLLING)

        repeat(12) { assertEquals(HostMeshStatus.State.ENROLLING, fixture.mesh.status().state) }
        assertEquals(HostMeshStatus.State.ERROR, fixture.mesh.status().state)
        assertEquals(configuration.oneUseAuthKey.value, fixture.store.value?.oneUseAuthKey)
    }

    @Test fun `adapter failure is typed and does not delete enrollment key`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)
        fixture.mesh.start()
        fixture.backend.snapshotFailure = IllegalStateException("secret must not escape")

        val status = fixture.mesh.status()

        assertEquals(HostMeshStatus.State.ERROR, status.state)
        assertEquals("IllegalStateException", status.detail)
        assertEquals(configuration.oneUseAuthKey.value, fixture.store.value?.oneUseAuthKey)
    }

    @Test fun `key deletion failure is explicit even after confirmed enrollment`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)
        fixture.mesh.start()
        fixture.backend.observation = BackendMeshSnapshot(BackendMeshSnapshot.State.RUNNING)
        fixture.store.failDeletion = true

        val status = fixture.mesh.status()

        assertEquals(HostMeshStatus.State.ERROR, status.state)
        assertEquals("auth_key_deletion_failed", status.detail)
    }

    @Test fun `revoke clears backend identity only after logout succeeds`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)

        fixture.mesh.clearIdentity()

        assertEquals(1, fixture.backend.logoutCalls)
        assertNull(fixture.store.value)
        assertEquals(HostMeshStatus.State.STOPPED, fixture.mesh.status().state)
    }

    @Test fun `logout failure preserves persisted recovery state`() {
        val fixture = fixture(permission = true)
        runBlocking { fixture.mesh.configure(configuration) }
        fixture.backend.logoutFailure = IllegalStateException("offline")

        assertThrows(IllegalStateException::class.java) { runBlocking { fixture.mesh.clearIdentity() } }

        assertEquals(configuration.controlUrl, fixture.store.value?.controlUrl)
        assertEquals(configuration.oneUseAuthKey.value, fixture.store.value?.oneUseAuthKey)
    }

    @Test fun `confirmed revoke clears configuration even when dedicated key deletion fails`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)
        fixture.store.failDeletion = true

        fixture.mesh.clearIdentity()

        assertNull(fixture.store.value)
        assertEquals(HostMeshStatus.State.STOPPED, fixture.mesh.status().state)
    }

    @Test fun `confirmed revoke does not retain key when final configuration clear fails`() {
        val fixture = fixture(permission = true)
        runBlocking { fixture.mesh.configure(configuration) }
        fixture.store.failClear = true

        assertThrows(IllegalStateException::class.java) { runBlocking { fixture.mesh.clearIdentity() } }

        assertEquals(configuration.controlUrl, fixture.store.value?.controlUrl)
        assertNull(fixture.store.value?.oneUseAuthKey)
    }

    @Test fun `status address collection is bounded`() = runBlocking {
        val fixture = fixture(permission = true)
        fixture.mesh.configure(configuration)
        fixture.mesh.start()
        fixture.backend.observation = BackendMeshSnapshot(
            BackendMeshSnapshot.State.RUNNING,
            addresses = (1..40).map { "100.64.0.$it" },
        )

        assertEquals(16, fixture.mesh.status().addresses.size)
    }

    @Test fun `invalid URL is rejected before persistence or adapter effects`() {
        val fixture = fixture(permission = true)
        val invalid = configuration.copy(controlUrl = "https://user@example.test/path?secret=x")

        assertThrows(IllegalArgumentException::class.java) { runBlocking { fixture.mesh.configure(invalid) } }

        assertNull(fixture.store.value)
        assertTrue(fixture.backend.configured.isEmpty())
    }

    private fun fixture(
        permission: Boolean,
        controlUrlPolicy: ControlUrlPolicy = ControlUrlPolicy.RELEASE,
    ): Fixture {
        val backend = FakeBackend()
        val store = FakeStore()
        return Fixture(
            LibtailscaleHostMesh(backend, store, { permission }, controlUrlPolicy),
            backend,
            store,
        )
    }

    private data class Fixture(
        val mesh: LibtailscaleHostMesh,
        val backend: FakeBackend,
        val store: FakeStore,
    )

    private class FakeBackend : HostMeshBackend {
        val configured = mutableListOf<HostMeshConfiguration>()
        val startKeys = mutableListOf<String?>()
        var observation = BackendMeshSnapshot(BackendMeshSnapshot.State.STOPPED)
        var configureFailure: Exception? = null
        var snapshotFailure: Exception? = null
        var logoutFailure: Exception? = null
        var logoutCalls = 0

        override suspend fun configure(configuration: HostMeshConfiguration) {
            configured += configuration
            configureFailure?.let { throw it }
        }
        override suspend fun start(oneUseAuthKey: String?) { startKeys += oneUseAuthKey }
        override suspend fun stop() { observation = BackendMeshSnapshot(BackendMeshSnapshot.State.STOPPED) }
        override suspend fun snapshot(): BackendMeshSnapshot {
            snapshotFailure?.let { throw it }
            return observation
        }
        override suspend fun logout() {
            logoutCalls += 1
            logoutFailure?.let { throw it }
            observation = BackendMeshSnapshot(BackendMeshSnapshot.State.STOPPED)
        }
    }

    private class FakeStore : MeshConfigurationStore {
        var value: PersistedMeshConfiguration? = null
        var failDeletion = false
        var failClear = false
        override suspend fun save(configuration: PersistedMeshConfiguration) { value = configuration }
        override suspend fun load(): PersistedMeshConfiguration? = value
        override suspend fun deleteOneUseAuthKey() {
            if (failDeletion) throw IllegalStateException("disk full")
            value = value?.copy(oneUseAuthKey = null)
        }
        override suspend fun clear() {
            if (failClear) throw IllegalStateException("disk full")
            value = null
        }
    }
}
