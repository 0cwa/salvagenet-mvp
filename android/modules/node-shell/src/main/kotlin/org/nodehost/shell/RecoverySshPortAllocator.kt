package org.nodehost.shell

import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.security.SecureRandom
import org.nodehost.qemu.RecoverySshHostPort

/** Selects one service-lifetime loopback forward with bounded collision retries. */
internal class RecoverySshPortAllocator(
    private val candidate: () -> Int = {
        MIN_PORT + SecureRandom().nextInt(MAX_PORT - MIN_PORT + 1)
    },
    private val attempts: Int = MAX_ATTEMPTS,
) {
    fun allocate(): RecoverySshHostPort {
        require(attempts in 1..MAX_ATTEMPTS)
        repeat(attempts) {
            val port = candidate()
            require(port in MIN_PORT..MAX_PORT) { "recovery SSH candidate is out of range" }
            val available = runCatching {
                ServerSocket().use { socket ->
                    socket.reuseAddress = false
                    socket.bind(InetSocketAddress(InetAddress.getLoopbackAddress(), port), 1)
                }
            }.isSuccess
            if (available) return RecoverySshHostPort(port)
        }
        error("recovery SSH loopback port allocation exhausted after $attempts attempts")
    }

    private companion object {
        const val MIN_PORT = 20_000
        const val MAX_PORT = 60_999
        const val MAX_ATTEMPTS = 16
    }
}
