package org.nodehost.api

import java.security.MessageDigest
import org.nodehost.core.ControllerAuthenticator
import org.nodehost.core.ControllerPrincipal
import org.nodehost.core.SecretValue

/** Temporary capability authenticator kept behind the permanent auth port. */
class MvpControllerAuthenticator(
    private val expectedCapability: SecretValue,
) : ControllerAuthenticator {
    override suspend fun authorize(
        authorization: String?,
        method: String,
        path: String,
    ): ControllerPrincipal? {
        if (authorization?.startsWith(BEARER_PREFIX) != true) return null
        val presented = authorization.removePrefix(BEARER_PREFIX)
        val accepted = MessageDigest.isEqual(
            presented.toByteArray(Charsets.UTF_8),
            expectedCapability.value.toByteArray(Charsets.UTF_8),
        )
        return if (accepted) {
            ControllerPrincipal(id = "mvp-controller", roles = setOf("admin"))
        } else {
            null
        }
    }

    private companion object {
        const val BEARER_PREFIX = "Bearer "
    }
}
