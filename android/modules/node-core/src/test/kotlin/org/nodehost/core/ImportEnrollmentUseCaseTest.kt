package org.nodehost.core

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import org.nodehost.model.*

class ImportEnrollmentUseCaseTest {
    @Test
    fun expiredEnrollmentIsRejectedBeforePersistence() {
        val repository = RecordingEnrollmentRepository()
        val useCase = ImportEnrollmentUseCase(repository, { OperationId("op-001") }, object : Clock {
            override fun epochMillis() = 2_000L
        })

        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { useCase.import(enrollment(expiresAt = 1_999L), "idempotency-key-0001", "request".toByteArray()) }
        }
        assertEquals(0, repository.acceptCount)
    }

    @Test
    fun exactReplayReturnsStableOperation() = runBlocking {
        val repository = RecordingEnrollmentRepository()
        var sequence = 0
        val useCase = ImportEnrollmentUseCase(repository, { OperationId("op-${++sequence}00") }, object : Clock {
            override fun epochMillis() = 1_000L
        })
        val first = useCase.import(enrollment(), "idempotency-key-0001", "request".toByteArray())
        val replay = useCase.import(enrollment(), "idempotency-key-0001", "request".toByteArray())

        assertEquals(first.id, replay.id)
        assertEquals(1, repository.persistCount)
    }

    private fun enrollment(expiresAt: Long = 2_000L) = NodeEnrollment(
        EnrollmentId("enrollment-001"),
        NodeName("node-01"),
        expiresAt,
        ControllerEnrollment("https://controller.invalid", "a".repeat(64), SensitiveValue("example-controller-token")),
        HostMeshEnrollment(
            "https://mesh.invalid",
            SensitiveValue("example-host-auth-key"),
            NodeName("node-01-host"),
            setOf("tag:node-host"),
        ),
        HostAccessEnrollment(SensitiveValue("example-controller-capability"), "controller-01"),
        GuestAccessEnrollment(
            "nodeadmin",
            GuestSshAuthorization.UserCertificateAuthority("ssh-ed25519 AAAAC3NzaExampleOnly"),
        ),
        ArtifactDefaults("https://artifacts.invalid", setOf(VmProfileId("ubuntu-2404-arm64-uefi"))),
        InitialRuntimeDefaults(VmProfileId("ubuntu-2404-arm64-uefi"), DesiredRuntimeState.STOPPED, 1024, 2, 8),
    )
}

private class RecordingEnrollmentRepository : EnrollmentRepository {
    private var enrollment: NodeEnrollment? = null
    private var operation: OperationRecord? = null
    var acceptCount = 0
    var persistCount = 0

    override suspend fun load(): NodeEnrollment? = enrollment

    override suspend fun acceptEnrollment(
        enrollment: NodeEnrollment,
        operation: OperationRecord,
    ): EnrollmentAcceptance {
        acceptCount += 1
        this.operation?.let { existing ->
            return if (existing.idempotencyKey == operation.idempotencyKey && existing.requestDigest == operation.requestDigest) {
                EnrollmentAcceptance.Replay(existing)
            } else {
                EnrollmentAcceptance.EnrollmentConflict
            }
        }
        this.enrollment = enrollment
        this.operation = operation
        persistCount += 1
        return EnrollmentAcceptance.Accepted
    }
}
