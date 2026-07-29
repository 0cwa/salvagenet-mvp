package org.nodehost.qemu

import android.net.LocalSocket
import android.net.LocalSocketAddress
import java.io.Closeable
import java.io.File
import java.io.InputStream
import java.io.OutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout

/** Fixed, internal command vocabulary. No raw QMP request can cross the module boundary. */
internal class QmpSession(
    private val socketPath: File,
    private val transportFactory: () -> QmpTransport = { AndroidQmpTransport() },
) : Closeable {
    private val mutex = Mutex()
    private var transport: QmpTransport? = null
    private var nextId = 1
    private var requestCount = 0

    suspend fun connect() = mutex.withLock {
        check(transport == null) { "QMP session already connected" }
        withTimeout(OPERATION_TIMEOUT_MS) {
            val candidate = transportFactory()
            try {
                candidate.connect(socketPath)
                require(candidate.readLineBounded().contains("\"QMP\"")) { "invalid QMP greeting" }
                candidate.writeLine(request("qmp_capabilities", nextId++))
                requireSuccess(candidate, nextId - 1)
                transport = candidate
            } catch (failure: Throwable) {
                candidate.close()
                throw failure
            }
        }
    }

    suspend fun queryStatus(): String = execute("query-status").let { response ->
        STATUS.find(response)?.groupValues?.get(1) ?: error("QMP status missing")
    }

    suspend fun systemPowerdown() { execute("system_powerdown") }
    suspend fun quit() { execute("quit") }

    private suspend fun execute(command: String): String = mutex.withLock {
        withTimeout(OPERATION_TIMEOUT_MS) {
            check(requestCount++ < MAX_REQUESTS) { "QMP session request limit exceeded" }
            val current = requireNotNull(transport) { "QMP session is not connected" }
            val id = nextId++
            current.writeLine(request(command, id))
            requireSuccess(current, id)
        }
    }

    private suspend fun requireSuccess(current: QmpTransport, id: Int): String {
        repeat(MAX_INTERLEAVED_EVENTS) {
            val response = current.readLineBounded()
            if (response.contains("\"id\":$id") || response.contains("\"id\": $id")) {
                require(!response.contains("\"error\"")) { "QMP command failed" }
                require(response.contains("\"return\"")) { "invalid QMP response" }
                return response
            }
        }
        error("QMP response limit exceeded")
    }

    override fun close() {
        transport?.close()
        transport = null
    }

    private fun request(command: String, id: Int) = "{\"execute\":\"$command\",\"id\":$id}"

    private companion object {
        const val OPERATION_TIMEOUT_MS = 3_000L
        const val MAX_REQUESTS = 64
        const val MAX_INTERLEAVED_EVENTS = 16
        val STATUS = Regex("\\\"status\\\"\\s*:\\s*\\\"([a-z-]{1,32})\\\"")
    }
}

internal interface QmpTransport : Closeable {
    suspend fun connect(path: File)
    suspend fun writeLine(line: String)
    suspend fun readLineBounded(): String
}

private class AndroidQmpTransport : QmpTransport {
    private val socket = LocalSocket()
    private lateinit var input: InputStream
    private lateinit var output: OutputStream

    override suspend fun connect(path: File) = withContext(Dispatchers.IO) {
        socket.soTimeout = SOCKET_TIMEOUT_MS
        socket.connect(LocalSocketAddress(path.path, LocalSocketAddress.Namespace.FILESYSTEM))
        input = socket.inputStream
        output = socket.outputStream
    }

    override suspend fun writeLine(line: String) = withContext(Dispatchers.IO) {
        val bytes = (line + "\r\n").toByteArray(Charsets.UTF_8)
        require(bytes.size <= MAX_QMP_LINE_BYTES)
        output.write(bytes)
        output.flush()
    }

    override suspend fun readLineBounded(): String = withContext(Dispatchers.IO) {
        val bytes = ArrayList<Byte>()
        while (bytes.size < MAX_QMP_LINE_BYTES) {
            val value = input.read()
            if (value < 0) error("QMP socket closed")
            if (value == '\n'.code) return@withContext bytes.toByteArray().toString(Charsets.UTF_8).trimEnd('\r')
            bytes += value.toByte()
        }
        error("QMP line exceeds $MAX_QMP_LINE_BYTES bytes")
    }

    override fun close() = socket.close()

    private companion object {
        const val SOCKET_TIMEOUT_MS = 3_000
        const val MAX_QMP_LINE_BYTES = 65_536
    }
}
