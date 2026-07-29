package org.nodehost.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ContractModelsTest {
    @Test
    fun secretsNeverRenderTheirValue() {
        val secret = SensitiveValue("not-a-real-secret-value")
        assertEquals("<redacted>", secret.toString())
    }

    @Test
    fun artifactRequiresDigestAndPositiveExpectedSize() {
        assertThrows(IllegalArgumentException::class.java) {
            ArtifactRef("ubuntu-image", "A".repeat(64), 1)
        }
        assertThrows(IllegalArgumentException::class.java) {
            ArtifactRef("ubuntu-image", "a".repeat(64), 0)
        }
    }

    @Test
    fun enrollmentDefaultMustReferenceAnAllowedProfile() {
        assertThrows(IllegalArgumentException::class.java) {
            enrollment(initialProfile = VmProfileId("k3s-worker-lab"))
        }
    }

    @Test
    fun sshAuthorizationRequiresAtLeastOneTrustedMechanism() {
        assertThrows(IllegalArgumentException::class.java) {
            GuestSshAuthorization.AuthorizedKeys(emptySet())
        }
    }

    private fun enrollment(initialProfile: VmProfileId) = NodeEnrollment(
        id = EnrollmentId("enrollment-001"),
        nodeName = NodeName("node-01"),
        expiresAtEpochMs = 4_102_444_800_000,
        controller = ControllerEnrollment(
            "https://controller.example.invalid",
            "a".repeat(64),
            SensitiveValue("example-enrollment-token"),
        ),
        hostMesh = HostMeshEnrollment(
            "https://mesh.example.invalid",
            SensitiveValue("example-host-auth-key"),
            NodeName("node-01-host"),
            setOf("tag:node-host"),
        ),
        hostAccess = HostAccessEnrollment(
            SensitiveValue("example-controller-capability"),
            "controller-01",
        ),
        guestAccess = GuestAccessEnrollment(
            "nodeadmin",
            GuestSshAuthorization.UserCertificateAuthority("ssh-ed25519 AAAAC3NzaExampleOnly"),
        ),
        artifacts = ArtifactDefaults(
            "https://artifacts.example.invalid",
            setOf(VmProfileId("ubuntu-2404-arm64-uefi")),
        ),
        initialRuntime = InitialRuntimeDefaults(initialProfile, DesiredRuntimeState.STOPPED, 1024, 2, 8),
    )
}
