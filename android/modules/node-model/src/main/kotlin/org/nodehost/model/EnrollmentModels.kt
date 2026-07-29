package org.nodehost.model

import java.net.URI
import java.net.URISyntaxException

private val hostnamePattern = Regex("[a-z0-9][a-z0-9-]{0,62}")
private val dnsLabelPattern = Regex("[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
private val sshPublicKeyPattern = Regex("ssh-(ed25519|rsa) [A-Za-z0-9+/=]+(?: .{1,128})?")
private val controllerIdPattern = Regex("[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

private fun requireHttpUri(
    value: String,
    allowedSchemes: Set<String>,
    userInfoAndFragmentAllowed: Boolean = true,
) {
    require(value.length in 1..2048) { "URI length is out of range" }
    val uri = try {
        URI(value)
    } catch (error: URISyntaxException) {
        throw IllegalArgumentException("invalid URI", error)
    }
    require(uri.isAbsolute && !uri.isOpaque && uri.scheme in allowedSchemes) { "invalid URI scheme" }
    require(uri.rawAuthority != null && uri.host != null) { "URI must have a host" }
    require(uri.port == -1 || uri.port in 1..65535) { "URI port is out of range" }
    if (!userInfoAndFragmentAllowed) {
        require(uri.rawUserInfo == null) { "URI userinfo is not allowed" }
        require(uri.rawFragment == null) { "URI fragment is not allowed" }
    }
    requirePublicHostSyntax(uri.host)
}

private fun requirePublicHostSyntax(uriHost: String) {
    val bracketed = uriHost.startsWith('[') && uriHost.endsWith(']')
    val host = uriHost.removePrefix("[").removeSuffix("]")
    require(!bracketed || host.contains(':')) { "bracketed host must be an IPv6 literal" }
    if (host.contains(':')) {
        // java.net.URI has already parsed and validated the bracketed IPv6 literal.
        require(host.all { it.isDigit() || it.lowercaseChar() in 'a'..'f' || it == ':' || it == '.' }) {
            "invalid IPv6 host"
        }
        return
    }
    if (host.all { it.isDigit() || it == '.' }) {
        val octets = host.split('.')
        require(octets.size == 4 && octets.all {
            it.isNotEmpty() && it.length <= 3 && it.toIntOrNull()?.let { value -> value in 0..255 } == true
        }) {
            "invalid IPv4 host"
        }
        return
    }
    require(host.length <= 253 && host.split('.').all(dnsLabelPattern::matches)) { "invalid DNS host" }
}

@JvmInline
value class SensitiveValue(val value: String) {
    init { require(value.length in 16..512) { "sensitive value length is out of range" } }
    override fun toString(): String = "<redacted>"
}

@JvmInline
value class EnrollmentId(val value: String) {
    init { require(Regex("[A-Za-z0-9][A-Za-z0-9._-]{7,127}").matches(value)) }
}

@JvmInline
value class NodeName(val value: String) {
    init { require(hostnamePattern.matches(value)) }
}

data class ControllerEnrollment(
    val endpoint: String,
    val spkiSha256: String,
    val oneTimeEnrollmentToken: SensitiveValue,
) {
    init {
        requireHttpUri(endpoint, setOf("https"), userInfoAndFragmentAllowed = false)
        require(Regex("[a-f0-9]{64}").matches(spkiSha256))
    }
}

data class HostMeshEnrollment(
    val controlUrl: String,
    val oneUseAuthKey: SensitiveValue,
    val hostname: NodeName,
    val expectedTags: Set<String>,
) {
    init {
        requireHttpUri(controlUrl, setOf("http", "https"))
        require(expectedTags.size in 1..8)
        require(expectedTags.all { Regex("tag:[a-z0-9][a-z0-9-]{0,62}").matches(it) })
    }
}

data class HostAccessEnrollment(
    val controllerCapability: SensitiveValue,
    val allowedControllerId: String,
) {
    init { require(controllerIdPattern.matches(allowedControllerId)) }
}

sealed interface GuestSshAuthorization {
    data class UserCertificateAuthority(val publicKey: String) : GuestSshAuthorization {
        init { require(publicKey.length in 24..16384 && sshPublicKeyPattern.matches(publicKey)) }
    }

    data class AuthorizedKeys(val publicKeys: Set<String>) : GuestSshAuthorization {
        init {
            require(publicKeys.size in 1..4)
            require(publicKeys.all { it.length in 24..16384 && sshPublicKeyPattern.matches(it) })
        }
    }
}

data class GuestAccessEnrollment(
    val sshUser: String,
    val authorization: GuestSshAuthorization,
) {
    init { require(Regex("[a-z_][a-z0-9_-]{0,31}").matches(sshUser)) }
}

data class ArtifactDefaults(
    val repositoryUrl: String,
    val profileIds: Set<VmProfileId>,
) {
    init {
        requireHttpUri(repositoryUrl, setOf("https"))
        require(profileIds.size in 1..16)
    }
}

data class InitialRuntimeDefaults(
    val profileId: VmProfileId,
    val desiredState: DesiredRuntimeState,
    val memoryMiB: Int,
    val vcpus: Int,
    val dataDiskGiB: Int,
) {
    init {
        require(desiredState != DesiredRuntimeState.ABSENT)
        require(memoryMiB in 256..16384)
        require(vcpus in 1..16)
        require(dataDiskGiB in 1..1024)
    }
}

data class NodeEnrollment(
    val id: EnrollmentId,
    val nodeName: NodeName,
    val expiresAtEpochMs: Long,
    val controller: ControllerEnrollment,
    val hostMesh: HostMeshEnrollment,
    val hostAccess: HostAccessEnrollment,
    val guestAccess: GuestAccessEnrollment,
    val artifacts: ArtifactDefaults,
    val initialRuntime: InitialRuntimeDefaults,
) {
    init {
        require(expiresAtEpochMs > 0)
        require(initialRuntime.profileId in artifacts.profileIds) {
            "initial runtime profile must be enrolled"
        }
    }
}
