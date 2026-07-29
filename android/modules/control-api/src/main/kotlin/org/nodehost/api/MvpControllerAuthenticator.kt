package org.nodehost.api

import java.security.MessageDigest
import org.nodehost.core.ControllerAuthenticator
import org.nodehost.core.ControllerPrincipal

/** Secret wrapper whose string representation never reveals the capability. */
class ControllerCapability(internal val value: String) {
    init { require(value.length in 24..512) { "invalid controller capability length" } }
    override fun toString(): String = "ControllerCapability([REDACTED])"
}

/** Temporary capability authenticator kept behind the permanent auth port. */
class MvpControllerAuthenticator(expectedCapability: ControllerCapability) : ControllerAuthenticator {
    private val expectedDigest = digest(expectedCapability.value)

    init {
        require(expectedCapability.value.length in 24..512) { "invalid expected controller capability length" }
    }

    override suspend fun authorize(
        authorization: String?,
        method: String,
        path: String,
    ): ControllerPrincipal? {
        if (authorization == null || authorization.length !in (BEARER_PREFIX.length + 1)..MAX_HEADER_LENGTH) return null
        if (!authorization.startsWith(BEARER_PREFIX)) return null
        val presented = authorization.substring(BEARER_PREFIX.length)
        // Compare fixed-size digests so capability length does not affect comparison timing.
        val accepted = MessageDigest.isEqual(digest(presented), expectedDigest)
        return if (accepted) ControllerPrincipal(id = "mvp-controller", roles = setOf("admin")) else null
    }

    private companion object {
        const val BEARER_PREFIX = "Bearer "
        const val MAX_HEADER_LENGTH = 1024
        fun digest(value: String): ByteArray = MessageDigest.getInstance("SHA-256")
            .digest(value.toByteArray(Charsets.UTF_8))
    }
}
