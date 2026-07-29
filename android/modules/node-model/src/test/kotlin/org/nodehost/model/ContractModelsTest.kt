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

    @Test
    fun controllerEndpointRequiresAConstrainedAbsoluteHttpsUri() {
        listOf(
            "http://controller.example.invalid",
            "https:controller.example.invalid",
            "https://user@controller.example.invalid",
            "https://controller.example.invalid/path#fragment",
            "https://controller_name.example.invalid",
            "https://${"a".repeat(64)}.example.invalid",
            "https://999.1.1.1",
            "https://[v1.controller]",
            "https://controller.example.invalid:${65536}",
            "https://controller.example.invalid/${"a".repeat(2049)}",
        ).forEach { endpoint ->
            assertThrows(endpoint, IllegalArgumentException::class.java) {
                ControllerEnrollment(endpoint, "a".repeat(64), SensitiveValue("example-enrollment-token"))
            }
        }

        listOf(
            "https://controller.example.invalid",
            "https://192.0.2.1:8443/v1/enroll?mode=one-time",
            "https://[2001:db8::1]/v1/enroll",
        ).forEach { endpoint ->
            ControllerEnrollment(endpoint, "a".repeat(64), SensitiveValue("example-enrollment-token"))
        }
    }

    @Test
    fun schemaPatternedEnrollmentValuesAreRejectedByDomainConstructors() {
        listOf("short", "-enrollment-001", "enrollment 001", "e".repeat(129)).forEach { value ->
            assertThrows(value, IllegalArgumentException::class.java) { EnrollmentId(value) }
        }
        listOf("-profile", "Profile-01", "profile_01", "p".repeat(65)).forEach { value ->
            assertThrows(value, IllegalArgumentException::class.java) { VmProfileId(value) }
        }
        listOf("-controller", "controller 01", "controller/01", "c".repeat(129)).forEach { value ->
            assertThrows(value, IllegalArgumentException::class.java) {
                HostAccessEnrollment(SensitiveValue("example-controller-capability"), value)
            }
        }
        listOf("A".repeat(64), "a".repeat(63), "g".repeat(64)).forEach { fingerprint ->
            assertThrows(fingerprint.take(16), IllegalArgumentException::class.java) {
                ControllerEnrollment("https://controller.example.invalid", fingerprint, SensitiveValue("example-enrollment-token"))
            }
        }
    }

    @Test
    fun schemaLengthAndUriLimitsAreEnforcedByDomainConstructors() {
        listOf("ssh-rsa ${"A".repeat(15)}", "ssh-rsa ${"A".repeat(16377)}").forEach { key ->
            assertThrows(IllegalArgumentException::class.java) {
                GuestSshAuthorization.UserCertificateAuthority(key)
            }
        }
        assertThrows(IllegalArgumentException::class.java) {
            HostMeshEnrollment(
                "http://mesh host.invalid",
                SensitiveValue("example-host-auth-key"),
                NodeName("node-01-host"),
                setOf("tag:node-host"),
            )
        }
        assertThrows(IllegalArgumentException::class.java) {
            ArtifactDefaults("https://artifact host.invalid", setOf(VmProfileId("ubuntu-2404-arm64-uefi")))
        }

        // Debug-lab mesh control remains the sole HTTP URL allowed by the pure contract.
        HostMeshEnrollment(
            "http://192.0.2.2:8080",
            SensitiveValue("example-host-auth-key"),
            NodeName("node-01-host"),
            setOf("tag:node-host"),
        )
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
