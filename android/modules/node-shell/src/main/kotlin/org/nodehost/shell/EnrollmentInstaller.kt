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
    suspend fun hasDurableState(): Boolean
    suspend fun enrollmentId(): String?
    suspend fun clear()
    suspend fun commit(enrollmentId: String): Boolean
    suspend fun beginBoot(profileId: org.nodehost.model.VmProfileId): String? = null
}

data class InstalledNode(
    val controllerAuthenticator: ControllerAuthenticator,
    val bootstrapProfile: GuestBootstrapProfile?,
)

/** Ordered integration boundary: persist authority before mesh/runtime effects, then wake reconciliation. */
class EnrollmentInstaller(
    private val enrollments: org.nodehost.core.EnrollmentRepository,
    operations: org.nodehost.store.RoomOperationRepository,
    private val mesh: HostMesh,
    private val bootstrapStore: GuestBootstrapStore,
    private val wakeReconciler: () -> Unit,
    private val clock: Clock,
    private val operationIds: OperationIdFactory = SecureOperationIdFactory(),
    private val isControllerRevoked: suspend (String) -> Boolean = { false },
    private val materializer: GuestBootstrapMaterializer = GuestBootstrapMaterializer(
        tokenFactory = { secureToken(32) },
    ),
) {
    private val importEnrollment = ImportEnrollmentUseCase(enrollments, operationIds, clock)
    private val applyRuntime = ApplyRuntimeUseCase(operations, operationIds)

    suspend fun install(
        rawEnrollment: ByteArray,
        rawGuestBootstrapSecret: ByteArray,
        enrollmentIdempotencyKey: String,
        approvedIssuerSpkiSha256: String,
    ): InstalledNode {
        val enrollment = EnrollmentJson.parse(rawEnrollment)
        require(MessageDigest.isEqual(enrollment.controller.spkiSha256.toByteArray(), approvedIssuerSpkiSha256.toByteArray())) {
            "enrollment issuer fingerprint was not approved"
        }
        val guestBootstrapSecret = GuestBootstrapSecretJson.parse(rawGuestBootstrapSecret)
        // Both hostile documents are fully parsed and cross-validated before either durable document can commit.
        materializer.validate(enrollment, guestBootstrapSecret)
        val canonicalImport = rawEnrollment + byteArrayOf(0) + rawGuestBootstrapSecret
        require(enrollmentIdempotencyKey.length in 16..200) { "invalid idempotency key length" }
        require(canonicalImport.isNotEmpty() && canonicalImport.size <= 1_048_576) { "canonical enrollment request is out of bounds" }
        require(enrollment.expiresAtEpochMs > clock.epochMillis()) { "enrollment has expired" }
        val stagedEnrollmentId = bootstrapStore.enrollmentId()
        require(stagedEnrollmentId == null || stagedEnrollmentId == enrollment.id.value) {
            "a different guest bootstrap enrollment is already staged"
        }
        val stagedNow = !bootstrapStore.hasDurableState()
        val materialized = if (stagedNow) {
            materializer.materialize(enrollment, guestBootstrapSecret).also { bootstrapStore.save(it) }
        } else null
        try {
            importEnrollment.import(enrollment, enrollmentIdempotencyKey, canonicalImport)
        } catch (failure: Throwable) {
            if (stagedNow) bootstrapStore.clear()
            throw failure
        }
        check(bootstrapStore.commit(enrollment.id.value)) { "guest bootstrap commit did not match enrollment authority" }

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
        // Erase duplicate enrollment credentials only after the mesh confirms durable identity.
        if (mesh.status().state == org.nodehost.core.HostMeshStatus.State.RUNNING) {
            (enrollments as? EncryptedEnrollmentRepository)?.clearConsumedOneTimeCredentials()
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
                isControllerRevoked,
            ),
            materialized?.profile,
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
    private val isRevoked: suspend (String) -> Boolean = { false },
) : ControllerAuthenticator {
    private val expectedDigest = digest(capability.value)

    override suspend fun authorize(authorization: String?, method: String, path: String): ControllerPrincipal? {
        if (authorization == null || !authorization.startsWith(BEARER) || authorization.length > MAX_HEADER_CHARS) return null
        val accepted = MessageDigest.isEqual(expectedDigest, digest(authorization.removePrefix(BEARER)))
        return if (accepted && !isRevoked(controllerId)) ControllerPrincipal(controllerId, setOf("admin")) else null
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
