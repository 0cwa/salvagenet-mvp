package org.nodehost.shell

import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.nodehost.api.RecoverySshGateway
import org.nodehost.api.RecoverySshSession
import org.nodehost.core.ControllerPrincipal
import org.nodehost.model.RuntimeId

/** VM-scoped recovery bridge. It can reach only the fixed QEMU loopback SSH forward. */
class LoopbackRecoverySshGateway(
    private val hostPort: Int = 19922,
) : RecoverySshGateway {
    private val active = AtomicBoolean(false)

    init { require(hostPort in 1024..65535) }

    override suspend fun open(vmId: RuntimeId, principal: ControllerPrincipal): RecoverySshSession {
        require(vmId == RuntimeId.DEFAULT) { "MVP supports one runtime" }
        require("admin" in principal.roles) { "recovery SSH requires controller admin role" }
        check(active.compareAndSet(false, true)) { "a recovery SSH session is already active" }
        return try {
            val socket = withContext(Dispatchers.IO) {
                Socket().apply {
                    soTimeout = IO_TIMEOUT_MILLIS
                    connect(InetSocketAddress(InetAddress.getLoopbackAddress(), hostPort), CONNECT_TIMEOUT_MILLIS)
                }
            }
            SocketRecoverySession(socket) { active.set(false) }
        } catch (failure: Throwable) {
            active.set(false)
            throw failure
        }
    }

    private class SocketRecoverySession(
        private val socket: Socket,
        private val released: () -> Unit,
    ) : RecoverySshSession {
        private val closed = AtomicBoolean(false)
        override suspend fun read(maxBytes: Int): ByteArray? = withContext(Dispatchers.IO) {
            require(maxBytes in 1..MAX_CHUNK_BYTES)
            val buffer = ByteArray(maxBytes)
            val count = socket.getInputStream().read(buffer)
            if (count < 0) null else buffer.copyOf(count)
        }
        override suspend fun write(bytes: ByteArray) = withContext(Dispatchers.IO) {
            require(bytes.isNotEmpty() && bytes.size <= MAX_CHUNK_BYTES)
            socket.getOutputStream().write(bytes)
            socket.getOutputStream().flush()
        }
        override suspend fun close() {
            if (closed.compareAndSet(false, true)) {
                withContext(Dispatchers.IO) { socket.close() }
                released()
            }
        }
    }

    private companion object {
        const val CONNECT_TIMEOUT_MILLIS = 5_000
        const val IO_TIMEOUT_MILLIS = 30_000
        const val MAX_CHUNK_BYTES = 64 * 1024
    }
}
