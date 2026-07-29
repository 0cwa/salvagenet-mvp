package org.nodehost.model

private val hostnamePattern = Regex("[a-z0-9][a-z0-9-]{0,62}")
private val sshPublicKeyPattern = Regex("ssh-(ed25519|rsa) [A-Za-z0-9+/=]+(?: .{1,128})?")

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
        require(endpoint.length <= 2048 && endpoint.startsWith("https://"))
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
        require(controlUrl.length <= 2048 && (controlUrl.startsWith("https://") || controlUrl.startsWith("http://")))
        require(expectedTags.size in 1..8)
        require(expectedTags.all { Regex("tag:[a-z0-9][a-z0-9-]{0,62}").matches(it) })
    }
}

data class HostAccessEnrollment(
    val controllerCapability: SensitiveValue,
    val allowedControllerId: String,
) {
    init { require(allowedControllerId.length in 1..128) }
}

sealed interface GuestSshAuthorization {
    data class UserCertificateAuthority(val publicKey: String) : GuestSshAuthorization {
        init { require(sshPublicKeyPattern.matches(publicKey)) }
    }

    data class AuthorizedKeys(val publicKeys: Set<String>) : GuestSshAuthorization {
        init {
            require(publicKeys.size in 1..4)
            require(publicKeys.all(sshPublicKeyPattern::matches))
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
        require(repositoryUrl.length <= 2048 && repositoryUrl.startsWith("https://"))
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
