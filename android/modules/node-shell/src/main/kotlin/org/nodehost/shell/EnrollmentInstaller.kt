package org.nodehost.shell

import java.security.SecureRandom
import java.util.Base64
import java.security.MessageDigest
import org.nodehost.core.ControllerAuthenticator
import org.nodehost.core.ControllerPrincipal
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.Clock
import org.nodehost.core.HostMesh
import org.nodehost.core.HostMeshConfiguration
import org.nodehost.core.ImportEnrollmentUseCase
import org.nodehost.core.OperationIdFactory
import org.nodehost.model.OperationId
import org.nodehost.model.RuntimeSpec

interface GuestBootstrapStore {
    suspend fun save(materialized: MaterializedGuestBootstrap)
}

data class InstalledNode(
    val controllerAuthenticator: ControllerAuthenticator,
    val bootstrapProfile: GuestBootstrapProfile,
)

/** Ordered integration boundary: persist authority before mesh/runtime effects, then wake reconciliation. */
class EnrollmentInstaller(
    enrollments: org.nodehost.core.EnrollmentRepository,
    operations: org.nodehost.store.RoomOperationRepository,
    private val mesh: HostMesh,
    private val bootstrapStore: GuestBootstrapStore,
    private val wakeReconciler: () -> Unit,
    private val clock: Clock,
    private val operationIds: OperationIdFactory = SecureOperationIdFactory(),
    private val materializer: GuestBootstrapMaterializer = GuestBootstrapMaterializer(
        tokenFactory = { secureToken(32) },
        callbackCapabilityFactory = { org.nodehost.model.SensitiveValue(secureToken(32)) },
    ),
) {
    private val importEnrollment = ImportEnrollmentUseCase(enrollments, operationIds, clock)
    private val applyRuntime = ApplyRuntimeUseCase(operations, operationIds)

    suspend fun install(
        rawEnrollment: ByteArray,
        guestMesh: GuestMeshBootstrap,
        enrollmentIdempotencyKey: String,
    ): InstalledNode {
        val enrollment = EnrollmentJson.parse(rawEnrollment)
        importEnrollment.import(enrollment, enrollmentIdempotencyKey, rawEnrollment)
        val materialized = materializer.materialize(enrollment, guestMesh)
        bootstrapStore.save(materialized)

        val status = mesh.status()
        if (status.state != org.nodehost.core.HostMeshStatus.State.RUNNING &&
            status.state != org.nodehost.core.HostMeshStatus.State.ENROLLING
        ) {
            mesh.configure(HostMeshConfiguration(
                enrollment.hostMesh.controlUrl,
                enrollment.hostMesh.hostname.value,
                enrollment.hostMesh.oneUseAuthKey,
            ))
            mesh.start()
        }

        val desired = RuntimeSpec(
            generation = 1,
            desiredState = enrollment.initialRuntime.desiredState,
            profileId = enrollment.initialRuntime.profileId,
            memoryMiB = enrollment.initialRuntime.memoryMiB,
            vcpus = enrollment.initialRuntime.vcpus,
            dataDiskGiB = enrollment.initialRuntime.dataDiskGiB,
        )
        val canonicalRuntime = "initial:${enrollment.id.value}:${desired.profileId.value}:${desired.desiredState}:${desired.memoryMiB}:${desired.vcpus}:${desired.dataDiskGiB}"
            .toByteArray()
        applyRuntime.apply(desired, "initial-${enrollment.id.value}".padEnd(16, '0'), canonicalRuntime)
        wakeReconciler()
        return InstalledNode(
            EnrolledControllerAuthenticator(
                enrollment.hostAccess.controllerCapability,
                enrollment.hostAccess.allowedControllerId,
            ),
            materialized.profile,
        )
    }

    private companion object {
        fun secureToken(bytes: Int): String = ByteArray(bytes).also(SecureRandom()::nextBytes)
            .let { Base64.getUrlEncoder().withoutPadding().encodeToString(it) }
    }
}

class EnrolledControllerAuthenticator(
    capability: org.nodehost.model.SensitiveValue,
    private val controllerId: String,
) : ControllerAuthenticator {
    private val expectedDigest = digest(capability.value)

    override suspend fun authorize(authorization: String?, method: String, path: String): ControllerPrincipal? {
        if (authorization == null || !authorization.startsWith(BEARER) || authorization.length > MAX_HEADER_CHARS) return null
        val accepted = MessageDigest.isEqual(expectedDigest, digest(authorization.removePrefix(BEARER)))
        return if (accepted) ControllerPrincipal(controllerId, setOf("admin")) else null
    }

    private companion object {
        const val BEARER = "Bearer "
        const val MAX_HEADER_CHARS = 1024
        fun digest(value: String) = MessageDigest.getInstance("SHA-256").digest(value.toByteArray())
    }
}

class SecureOperationIdFactory : OperationIdFactory {
    override fun newId(): OperationId = OperationId(
        ByteArray(18).also(SecureRandom()::nextBytes)
            .let { "op-" + Base64.getUrlEncoder().withoutPadding().encodeToString(it) },
    )
}
