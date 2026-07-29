package org.nodehost.mesh

import java.io.ByteArrayOutputStream
import kotlinx.coroutines.runBlocking
import libtailscale.Application
import libtailscale.FileParts
import libtailscale.InputStream
import libtailscale.LocalAPIResponse
import libtailscale.NotificationCallback
import libtailscale.NotificationManager
import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.nodehost.core.HostMeshConfiguration
import org.nodehost.model.SensitiveValue

class OfficialLibtailscaleAdapterTest {
    private val configuration = HostMeshConfiguration(
        "https://headscale.example.test",
        "phone-node",
        SensitiveValue("fake-one-use-key-abcdefghijklmnop"),
    )

    @Test fun `official prefs request carries typed URL and hostname`() {
        val call = OfficialLocalApiRequests.configure(configuration)
        val body = JSONObject(String(call.body!!))

        assertEquals("PATCH", call.method)
        assertEquals("prefs", call.endpoint)
        assertEquals(configuration.controlUrl, body.getString("ControlURL"))
        assertEquals(configuration.hostname, body.getString("Hostname"))
        assertEquals(true, body.getBoolean("ControlURLSet"))
        assertEquals(true, body.getBoolean("HostnameSet"))
        assertFalse(body.has("AuthKey"))
    }

    @Test fun `official start request carries key only when enrollment still needs it`() {
        val enrollment = JSONObject(String(OfficialLocalApiRequests.start(configuration.oneUseAuthKey.value).body!!))
        val restart = JSONObject(String(OfficialLocalApiRequests.start(null).body!!))

        assertEquals(configuration.oneUseAuthKey.value, enrollment.getString("AuthKey"))
        assertFalse(restart.has("AuthKey"))
    }

    @Test fun `VPN revoke request clears wanted-running state`() {
        val call = OfficialLocalApiRequests.stop()
        val body = JSONObject(String(call.body!!))

        assertEquals("PATCH", call.method)
        assertEquals("prefs", call.endpoint)
        assertEquals(false, body.getBoolean("WantRunning"))
        assertEquals(true, body.getBoolean("WantRunningSet"))
    }

    @Test fun `confirmed VPN revoke deletes persisted one-use key`() = runBlocking {
        val effects = mutableListOf<String>()

        revokeVpn(
            stopBackend = { effects += "backend_stopped" },
            deleteOneUseAuthKey = { effects += "key_deleted" },
        )

        assertEquals(listOf("backend_stopped", "key_deleted"), effects)
    }

    @Test fun `failed VPN revoke retains key for explicit retry`() {
        var deletionCalled = false

        assertThrows(IllegalStateException::class.java) {
            runBlocking {
                revokeVpn(
                    stopBackend = { throw IllegalStateException("offline") },
                    deleteOneUseAuthKey = { deletionCalled = true },
                )
            }
        }

        assertFalse(deletionCalled)
    }

    @Test fun `sticky service restart budget is bounded and reset by explicit start`() {
        val budget = VpnRestartBudget(3)

        repeat(3) { assertEquals(true, budget.allowSystemRestart()) }
        assertEquals(false, budget.allowSystemRestart())
        budget.onExplicitStart()
        assertEquals(true, budget.allowSystemRestart())
    }

    @Test fun `release native callback emits no upstream lines`() {
        val emitted = mutableListOf<String>()
        val callback = NativeLogCallback(diagnosticsEnabled = false, sink = emitted::add)

        callback.emit("backend raw line with tskey-" + "auth-super-secret")

        assertTrue(emitted.isEmpty())
    }

    @Test fun `debug native callback bounds and redacts sensitive diagnostics`() {
        val emitted = mutableListOf<String>()
        val callback = NativeLogCallback(diagnosticsEnabled = true, sink = emitted::add)
        val authKey = "tskey-" + "auth-abc_123-secret"
        val secrets = listOf(
            authKey,
            "bearer-token-value",
            "password-value",
            "api-key-value",
            "json-key-value",
            "query-secret-value",
        )
        callback.emit(
            "auth=$authKey " +
                "Authorization=Bearer bearer-token-value password='password-value' " +
                "api_key=api-key-value {\"AuthKey\":\"json-key-value\"} " +
                "url=https://user:pass@example.test/path?token=query-secret-value " +
                "tail=${"x".repeat(8 * 1024)}",
        )

        val diagnostic = emitted.single()
        assertTrue(diagnostic.length <= 1024)
        secrets.forEach { assertFalse("diagnostic leaked $it", diagnostic.contains(it, ignoreCase = true)) }
        assertFalse(diagnostic.contains("https://"))
        assertTrue(diagnostic.contains("[REDACTED]") || diagnostic.contains("[AUTH_KEY_REDACTED]"))
        assertTrue(diagnostic.contains("[URL_REDACTED]"))
    }

    @Test fun `local api adapter applies bounded timeout path method and body`() = runBlocking {
        val application = FakeApplication(statusCode = 200, responseBody = "ok".toByteArray())
        val result = OfficialLocalApiClient { application }.execute(
            LocalApiCall("PATCH", "prefs", "request".toByteArray()),
        )

        assertArrayEquals("ok".toByteArray(), result)
        assertEquals(5_000L, application.timeoutMillis)
        assertEquals("PATCH", application.method)
        assertEquals("/localapi/v0/prefs", application.endpoint)
        assertArrayEquals("request".toByteArray(), application.requestBody)
    }

    @Test fun `local api adapter rejects failed and oversized responses`() {
        val failed = FakeApplication(503, "unavailable".toByteArray())
        assertThrows(IllegalStateException::class.java) {
            runBlocking { OfficialLocalApiClient { failed }.execute(LocalApiCall("GET", "status")) }
        }

        val oversized = FakeApplication(200, ByteArray(64 * 1024 + 1))
        assertThrows(IllegalStateException::class.java) {
            runBlocking { OfficialLocalApiClient { oversized }.execute(LocalApiCall("GET", "status")) }
        }
    }

    @Test fun `local api adapter rejects oversized caller body before generated binding`() {
        val application = FakeApplication(200, ByteArray(0))

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                OfficialLocalApiClient { application }.execute(
                    LocalApiCall("POST", "start", ByteArray(4 * 1024 + 1)),
                )
            }
        }
        assertNull(application.method)
    }

    private class FakeApplication(
        private val statusCode: Long,
        private val responseBody: ByteArray,
    ) : Application {
        var timeoutMillis: Long? = null
        var method: String? = null
        var endpoint: String? = null
        var requestBody: ByteArray? = null

        override fun callLocalAPI(
            timeoutMillis: Long,
            method: String,
            endpoint: String,
            body: InputStream?,
        ): LocalAPIResponse {
            this.timeoutMillis = timeoutMillis
            this.method = method
            this.endpoint = endpoint
            requestBody = body?.readAll()
            return FakeResponse(statusCode, responseBody)
        }

        override fun callLocalAPIMultipart(
            timeoutMillis: Long,
            method: String?,
            endpoint: String?,
            parts: FileParts?,
        ): LocalAPIResponse = throw UnsupportedOperationException()

        override fun notifyPolicyChanged() = Unit
        override fun setClientLoggingEnabled(enabled: Boolean) = Unit
        override fun watchNotifications(mask: Long, callback: NotificationCallback?): NotificationManager =
            object : NotificationManager { override fun stop() = Unit }

        private fun InputStream.readAll(): ByteArray {
            val output = ByteArrayOutputStream()
            while (true) {
                val next = read()
                if (next.isEmpty()) break
                output.write(next)
            }
            close()
            return output.toByteArray()
        }
    }

    private class FakeResponse(
        private val status: Long,
        private val body: ByteArray,
    ) : LocalAPIResponse {
        override fun statusCode(): Long = status
        override fun bodyBytes(): ByteArray = body
        override fun bodyInputStream(): InputStream? = null
    }
}
