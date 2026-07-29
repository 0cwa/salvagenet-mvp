package org.nodehost.shell

import java.io.BufferedReader
import java.io.Closeable
import java.io.InputStreamReader
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlinx.coroutines.runBlocking

/** Loopback-only, bounded NoCloud/bootstrap endpoint reachable through QEMU SLIRP at 10.0.2.2. */
class BootstrapMetadataServer(
    private val store: AndroidGuestBootstrapStore,
    private val port: Int = 8080,
) : Closeable {
    private val executor: ExecutorService = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "nodehost-bootstrap-http").apply { isDaemon = true }
    }
    @Volatile private var server: ServerSocket? = null

    @Synchronized fun start() {
        if (server != null) return
        val opened = ServerSocket(port, MAX_PENDING_CONNECTIONS, InetAddress.getLoopbackAddress()).apply {
            soTimeout = ACCEPT_POLL_MILLIS
        }
        server = opened
        executor.execute { acceptLoop(opened) }
    }

    private fun acceptLoop(opened: ServerSocket) {
        while (!opened.isClosed) {
            try {
                opened.accept().use(::handle)
            } catch (_: SocketTimeoutException) {
                // Poll closure without retaining an uninterruptible accept during service shutdown.
            } catch (failure: Exception) {
                if (!opened.isClosed) android.util.Log.e(TAG, "bootstrap request failed", failure)
            }
        }
    }

    private fun handle(socket: Socket) {
        socket.soTimeout = REQUEST_TIMEOUT_MILLIS
        val reader = BufferedReader(InputStreamReader(socket.getInputStream(), Charsets.US_ASCII), 4096)
        val requestLine = reader.readLine() ?: return
        require(requestLine.length <= MAX_REQUEST_LINE_CHARS)
        val parts = requestLine.split(' ')
        require(parts.size == 3 && parts[2] == "HTTP/1.1")
        var authorization: String? = null
        var headerBytes = requestLine.length
        while (true) {
            val line = reader.readLine() ?: return
            headerBytes += line.length
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
        output.write("HTTP/1.1 ${statusAndBody.first}\r\nContent-Type: $contentType\r\nContent-Length: ${body.size}\r\nConnection: close\r\n\r\n".toByteArray())
        output.write(body)
        output.flush()
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
            "vendor-data" -> "#cloud-config\n".toByteArray()
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
        executor.shutdownNow()
    }

    private companion object {
        const val TAG = "NodeHostBootstrap"
        const val MAX_PENDING_CONNECTIONS = 4
        const val ACCEPT_POLL_MILLIS = 500
        const val REQUEST_TIMEOUT_MILLIS = 5_000
        const val MAX_REQUEST_LINE_CHARS = 2048
        const val MAX_HEADER_CHARS = 16 * 1024
        const val MAX_AUTHORIZATION_CHARS = 256
        val PATH = Regex("/v1/bootstrap/([A-Za-z0-9_-]{32,128})/(meta-data|user-data|vendor-data|bootstrap-secret)")
    }
}
