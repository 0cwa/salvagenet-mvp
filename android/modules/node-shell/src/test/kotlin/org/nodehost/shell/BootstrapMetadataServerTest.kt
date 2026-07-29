package org.nodehost.shell

import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class BootstrapMetadataServerTest {
    private val token = "t".repeat(43)

    @Test fun occupiedContractPortFailsImmediatelyAndExplicitly() {
        ServerSocket(0, 1, InetAddress.getLoopbackAddress()).use { occupied ->
            val failure = runCatching { BootstrapMetadataServer(RecordingStore(), occupied.localPort).start() }.exceptionOrNull()
            assertTrue(failure is IllegalStateException)
            assertTrue(failure?.message.orEmpty().contains("public NoCloud contract"))
        }
    }

    @Test fun oversizedRequestLineIsRejectedBeforeStoreAccess() {
        val store = RecordingStore()
        BootstrapMetadataServer(store, 0).use { server ->
            server.start()
            Socket(InetAddress.getLoopbackAddress(), server.boundPort).use { socket ->
                socket.soTimeout = 2_000
                socket.getOutputStream().write(("G".repeat(2_049) + "\r\n\r\n").toByteArray())
                runCatching { socket.getInputStream().readBytes() }
            }
        }
        assertEquals(0, store.profileCalls.get())
    }

    @Test fun readinessCapabilityIsSeparateFromBootstrapTokenAndConsumedAtomically() {
        val store = ReadinessStore()
        BootstrapMetadataServer(store, 0).use { server ->
            server.start()
            val fresh = request(server.boundPort, "GET /v1/bootstrap/readiness-capability HTTP/1.1\r\nAuthorization: Bearer root-capability-0001\r\n\r\n")
            assertTrue(fresh.contains("200 OK"))
            assertTrue(fresh.endsWith("fresh-capability-0001"))
            val accepted = request(server.boundPort, "POST /v1/bootstrap/ready HTTP/1.1\r\nAuthorization: Bearer fresh-capability-0001\r\n\r\n")
            assertTrue(accepted.contains("204 No Content"))
            assertTrue(request(server.boundPort, "POST /v1/bootstrap/ready HTTP/1.1\r\nAuthorization: Bearer fresh-capability-0001\r\n\r\n").contains("401 Unauthorized"))
            assertTrue(request(server.boundPort, "POST /v1/bootstrap/ready HTTP/1.1\r\nAuthorization: Bearer $token\r\n\r\n").contains("401 Unauthorized"))
        }
    }

    @Test fun requestExecutionNeverExceedsTheFixedConcurrencyBound() {
        val store = RecordingStore(delayMillis = 150)
        BootstrapMetadataServer(store, 0).use { server ->
            server.start()
            val clients = Executors.newFixedThreadPool(12)
            val finished = CountDownLatch(12)
            repeat(12) {
                clients.execute {
                    runCatching {
                        Socket(InetAddress.getLoopbackAddress(), server.boundPort).use { socket ->
                            socket.soTimeout = 3_000
                            socket.getOutputStream().write("GET /v1/bootstrap/$token/meta-data HTTP/1.1\r\nHost: guest\r\n\r\n".toByteArray())
                            socket.getInputStream().readBytes()
                        }
                    }
                    finished.countDown()
                }
            }
            assertTrue(finished.await(5, TimeUnit.SECONDS))
            clients.shutdownNow()
        }
        assertTrue(store.maximumActive.get() in 1..3)
    }

    private fun request(port: Int, request: String): String = Socket(InetAddress.getLoopbackAddress(), port).use { socket ->
        socket.soTimeout = 2_000
        socket.getOutputStream().write(request.toByteArray())
        socket.getInputStream().readBytes().toString(Charsets.UTF_8)
    }

    private class ReadinessStore : BootstrapRequestStore {
        private var fresh: String? = "fresh-capability-0001"
        override suspend fun profile(presentedToken: String) = null
        override suspend fun vendorData(presentedToken: String) = null
        override suspend fun redeem(presentedToken: String) = null
        override suspend fun readinessCapability(presentedRootCapability: String) =
            if (presentedRootCapability == "root-capability-0001") fresh?.toByteArray() else null
        override suspend fun markGuestReady(presentedCapability: String): Boolean {
            if (fresh != presentedCapability) return false
            fresh = null
            return true
        }
    }

    private inner class RecordingStore(private val delayMillis: Long = 0) : BootstrapRequestStore {
        val profileCalls = AtomicInteger()
        val maximumActive = AtomicInteger()
        private val active = AtomicInteger()

        override suspend fun profile(presentedToken: String): GuestBootstrapProfile? {
            profileCalls.incrementAndGet()
            val now = active.incrementAndGet()
            maximumActive.updateAndGet { maxOf(it, now) }
            try {
                if (delayMillis > 0) Thread.sleep(delayMillis)
                return if (presentedToken == token) GuestBootstrapProfile(
                    "enroll-test", "ubuntu-2404-arm64-uefi", token, "/v1/bootstrap/$token/", "instance-id: default\n", "#cloud-config\n",
                ) else null
            } finally { active.decrementAndGet() }
        }

        override suspend fun vendorData(presentedToken: String) = "#cloud-config\n".toByteArray()
        override suspend fun redeem(presentedToken: String): ByteArray? = null
        override suspend fun markGuestReady(presentedCapability: String) = false
    }
}
