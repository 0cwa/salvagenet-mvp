package org.nodehost.shell

import java.io.Closeable
import java.io.InputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.runBlocking

internal interface BootstrapRequestStore {
    suspend fun profile(presentedToken: String): GuestBootstrapProfile?
    suspend fun vendorData(presentedToken: String): ByteArray?
    suspend fun redeem(presentedToken: String): ByteArray?
    suspend fun markGuestReady(presentedCapability: String): Boolean
}

/** Loopback-only, bounded NoCloud/bootstrap endpoint reachable through QEMU SLIRP at 10.0.2.2. */
internal class BootstrapMetadataServer(
    private val store: BootstrapRequestStore,
    private val port: Int = 8080,
) : Closeable {
    private val acceptExecutor: ExecutorService = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "nodehost-bootstrap-accept").apply { isDaemon = true }
    }
    private val requestExecutor = ThreadPoolExecutor(
        MAX_ACTIVE_REQUESTS, MAX_ACTIVE_REQUESTS, 0L, TimeUnit.MILLISECONDS,
        ArrayBlockingQueue(MAX_QUEUED_REQUESTS),
        { runnable -> Thread(runnable, "nodehost-bootstrap-request").apply { isDaemon = true } },
        ThreadPoolExecutor.AbortPolicy(),
    )
    private val openSockets = ConcurrentHashMap.newKeySet<Socket>()
    @Volatile private var server: ServerSocket? = null
    internal val boundPort: Int get() = server?.localPort ?: error("bootstrap server is not started")

    @Synchronized fun start() {
        if (server != null) return
        val opened = ServerSocket(port, MAX_PENDING_CONNECTIONS, InetAddress.getLoopbackAddress()).apply {
            soTimeout = ACCEPT_POLL_MILLIS
        }
        server = opened
        acceptExecutor.execute { acceptLoop(opened) }
    }

    private fun acceptLoop(opened: ServerSocket) {
        while (!opened.isClosed) {
            try {
                val socket = opened.accept()
                openSockets += socket
                try {
                    requestExecutor.execute {
                        try { socket.use(::handle) }
                        catch (failure: Exception) { android.util.Log.w(TAG, "bootstrap request rejected class=${failure::class.java.simpleName}") }
                        finally { openSockets -= socket }
                    }
                } catch (_: java.util.concurrent.RejectedExecutionException) {
                    openSockets -= socket
                    socket.close()
                }
            } catch (_: SocketTimeoutException) {
                // Poll closure without retaining an uninterruptible accept during service shutdown.
            } catch (failure: Exception) {
                if (!opened.isClosed) android.util.Log.e(TAG, "bootstrap request failed", failure)
            }
        }
    }

    private fun handle(socket: Socket) {
        val headerDeadlineNanos = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(TOTAL_HEADER_TIMEOUT_MILLIS.toLong())
        socket.soTimeout = TOTAL_HEADER_TIMEOUT_MILLIS
        val input = socket.getInputStream()
        val requestLine = readAsciiLine(input, MAX_REQUEST_LINE_CHARS) ?: return
        val parts = requestLine.split(' ')
        require(parts.size == 3 && parts[2] == "HTTP/1.1")
        var authorization: String? = null
        var headerBytes = requestLine.length
        while (true) {
            val remainingMillis = TimeUnit.NANOSECONDS.toMillis(headerDeadlineNanos - System.nanoTime()).coerceAtLeast(1)
            check(System.nanoTime() < headerDeadlineNanos) { "request header deadline exceeded" }
            socket.soTimeout = remainingMillis.coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
            val line = readAsciiLine(input, MAX_HEADER_CHARS - headerBytes) ?: return
            headerBytes += line.length + 2
            require(headerBytes <= MAX_HEADER_CHARS)
            if (line.isEmpty()) break
            val separator = line.indexOf(':')
            require(separator > 0)
            if (line.substring(0, separator).equals("Authorization", ignoreCase = true)) {
                authorization = line.substring(separator + 1).trim().take(MAX_AUTHORIZATION_CHARS)
            }
        }
        val statusAndBody = runBlocking { route(parts[0], parts[1], authorization) }
        val output = socket.getOutputStream()
        val body = statusAndBody.second
        val contentType = if (parts[1].endsWith("bootstrap-secret")) "application/json" else "text/plain"
        try {
            output.write("HTTP/1.1 ${statusAndBody.first}\r\nContent-Type: $contentType\r\nContent-Length: ${body.size}\r\nConnection: close\r\n\r\n".toByteArray())
            output.write(body)
            output.flush()
        } finally { body.fill(0) }
    }

    private fun readAsciiLine(input: InputStream, maximumChars: Int): String? {
        require(maximumChars > 0) { "HTTP headers exceed size limit" }
        val line = StringBuilder(minOf(maximumChars, 256))
        while (true) {
            val value = input.read()
            if (value < 0) return if (line.isEmpty()) null else line.toString().trimEnd('\r')
            require(value in 0..0x7f) { "HTTP headers must be ASCII" }
            if (value == '\n'.code) return line.toString().trimEnd('\r')
            require(line.length < maximumChars) { "HTTP header line exceeds size limit" }
            line.append(value.toChar())
        }
    }

    private suspend fun route(method: String, path: String, authorization: String?): Pair<String, ByteArray> {
        if (method == "POST" && path == "/v1/bootstrap/ready") {
            val capability = authorization?.removePrefix("Bearer ").takeUnless { it == authorization }.orEmpty()
            return if (store.markGuestReady(capability)) "204 No Content" to ByteArray(0)
            else "401 Unauthorized" to ByteArray(0)
        }
        val match = PATH.matchEntire(path) ?: return "404 Not Found" to ByteArray(0)
        if (method != "GET") return "405 Method Not Allowed" to ByteArray(0)
        val token = match.groupValues[1]
        val resource = match.groupValues[2]
        val profile = store.profile(token) ?: return "404 Not Found" to ByteArray(0)
        val body = when (resource) {
            "meta-data" -> profile.metaData.toByteArray()
            "user-data" -> profile.userData.toByteArray()
            "vendor-data" -> store.vendorData(token) ?: return "404 Not Found" to ByteArray(0)
            "bootstrap-secret" -> {
                if (authorization != "Bearer $token") return "401 Unauthorized" to ByteArray(0)
                store.redeem(token) ?: return "410 Gone" to ByteArray(0)
            }
            else -> return "404 Not Found" to ByteArray(0)
        }
        return "200 OK" to body
    }

    @Synchronized override fun close() {
        server?.close()
        server = null
        openSockets.forEach { runCatching { it.close() } }
        openSockets.clear()
        acceptExecutor.shutdownNow()
        requestExecutor.shutdownNow()
    }

    private companion object {
        const val TAG = "NodeHostBootstrap"
        const val MAX_PENDING_CONNECTIONS = 4
        const val MAX_ACTIVE_REQUESTS = 3
        const val MAX_QUEUED_REQUESTS = 3
        const val ACCEPT_POLL_MILLIS = 500
        const val TOTAL_HEADER_TIMEOUT_MILLIS = 5_000
        const val MAX_REQUEST_LINE_CHARS = 2048
        const val MAX_HEADER_CHARS = 16 * 1024
        const val MAX_AUTHORIZATION_CHARS = 256
        val PATH = Regex("/v1/bootstrap/([A-Za-z0-9_-]{32,128})/(meta-data|user-data|vendor-data|bootstrap-secret)")
    }
}
