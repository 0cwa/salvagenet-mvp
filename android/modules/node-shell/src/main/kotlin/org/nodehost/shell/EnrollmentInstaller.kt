package org.nodehost.shell

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.Clock
import org.nodehost.core.ControllerAuthenticator
import org.nodehost.core.ControllerPrincipal
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

internal fun interface EnrollmentBoundaryHook {
    suspend fun after(phase: EnrollmentPhase)
}

/** Durable ordered enrollment transaction. Each effect is replay-safe before the next phase is recorded. */
internal class EnrollmentInstaller(
    private val enrollments: org.nodehost.core.EnrollmentRepository,
    operations: org.nodehost.store.RoomOperationRepository,
    private val mesh: HostMesh,
    private val bootstrapStore: GuestBootstrapStore,
    private val wakeReconciler: () -> Unit,
    private val clock: Clock,
    private val phaseStore: EnrollmentPhaseStore = VolatileEnrollmentPhaseStore(),
    private val operationIds: OperationIdFactory = SecureOperationIdFactory(),
    private val isControllerRevoked: suspend (String) -> Boolean = { false },
    private val materializer: GuestBootstrapMaterializer = GuestBootstrapMaterializer(
        tokenFactory = { secureToken(32) },
    ),
    private val boundaryHook: EnrollmentBoundaryHook = EnrollmentBoundaryHook {},
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
        materializer.validate(enrollment, guestBootstrapSecret)
        val canonicalImport = rawEnrollment + byteArrayOf(0) + rawGuestBootstrapSecret
        require(enrollmentIdempotencyKey.length in 16..200) { "invalid idempotency key length" }
        require(canonicalImport.isNotEmpty() && canonicalImport.size <= 1_048_576) { "canonical enrollment request is out of bounds" }
        require(enrollment.expiresAtEpochMs > clock.epochMillis()) { "enrollment has expired" }

        val requestDigest = MessageDigest.getInstance("SHA-256").digest(canonicalImport)
            .joinToString("") { "%02x".format(it) }
        val existingPhase = phaseStore.load()
        require(existingPhase == null || (
            existingPhase.enrollmentId == enrollment.id.value &&
                existingPhase.idempotencyKey == enrollmentIdempotencyKey &&
                existingPhase.requestDigest == requestDigest
            )) { "a conflicting enrollment transaction is already durable" }
        val stagedEnrollmentId = bootstrapStore.enrollmentId()
        require(stagedEnrollmentId == null || stagedEnrollmentId == enrollment.id.value) {
            "a different guest bootstrap enrollment is already staged"
        }
        var materialized: MaterializedGuestBootstrap? = null
        var phase = existingPhase
        if (phase == null) {
            if (!bootstrapStore.hasDurableState()) {
                materialized = materializer.materialize(enrollment, guestBootstrapSecret)
                bootstrapStore.save(materialized)
            }
            phase = EnrollmentRecoveryState(
                enrollment.id.value, EnrollmentPhase.VALIDATED_STAGED, rawEnrollment.copyOf(),
                rawGuestBootstrapSecret.copyOf(), enrollmentIdempotencyKey, requestDigest, approvedIssuerSpkiSha256,
            )
            phaseStore.save(phase)
            boundaryHook.after(EnrollmentPhase.VALIDATED_STAGED)
        }
        return resume(phase, enrollment, canonicalImport, materialized)
    }

    suspend fun markBootstrapCommittedApiReady() {
        val phase = phaseStore.load() ?: return
        require(phase.phase >= EnrollmentPhase.HOST_MESH_ENROLLED_KEY_ERASED) {
            "API cannot become ready before host mesh enrollment"
        }
        if (phase.phase != EnrollmentPhase.BOOTSTRAP_COMMITTED_API_READY) {
            phaseStore.save(phase.copy(phase = EnrollmentPhase.BOOTSTRAP_COMMITTED_API_READY))
            boundaryHook.after(EnrollmentPhase.BOOTSTRAP_COMMITTED_API_READY)
        }
    }

    /** Startup recovery deletes an unauthoritative stage and resumes every authoritative boundary. */
    suspend fun recoverOnStartup(): InstalledNode? {
        val phase = phaseStore.load()
        val authority = enrollments.load()
        if (authority == null) {
            if (phase?.phase == EnrollmentPhase.VALIDATED_STAGED || bootstrapStore.hasDurableState()) {
                bootstrapStore.clear()
                phaseStore.clear()
            }
            return null
        }
        if (phase == null) return resumeExistingAuthority(authority)
        require(phase.enrollmentId == authority.id.value) { "enrollment phase does not match authority" }
        return resume(phase, authority, null, null)
    }

    private suspend fun resume(
        initialPhase: EnrollmentRecoveryState,
        parsedEnrollment: org.nodehost.model.NodeEnrollment,
        canonicalImport: ByteArray?,
        bootstrapProfile: MaterializedGuestBootstrap?,
    ): InstalledNode {
        var phase = initialPhase
        var enrollment = enrollments.load() ?: parsedEnrollment
        if (phase.phase == EnrollmentPhase.VALIDATED_STAGED) {
            val canonical = canonicalImport ?: (phase.rawEnrollment + byteArrayOf(0) + phase.rawGuestBootstrapSecret)
            importEnrollment.import(enrollment, phase.idempotencyKey, canonical)
            enrollment = requireNotNull(enrollments.load()) { "accepted enrollment authority is unavailable" }
            phase = phase.copy(
                phase = EnrollmentPhase.AUTHORITY_ACCEPTED,
                rawEnrollment = ByteArray(0),
                rawGuestBootstrapSecret = ByteArray(0),
            )
            phaseStore.save(phase)
            boundaryHook.after(EnrollmentPhase.AUTHORITY_ACCEPTED)
        }
        if (phase.phase == EnrollmentPhase.AUTHORITY_ACCEPTED) {
            applyInitialRuntime(enrollment)
            phase = phase.copy(phase = EnrollmentPhase.INITIAL_RUNTIME_ACCEPTED)
            phaseStore.save(phase)
            boundaryHook.after(EnrollmentPhase.INITIAL_RUNTIME_ACCEPTED)
        }
        if (phase.phase == EnrollmentPhase.INITIAL_RUNTIME_ACCEPTED) {
            enrollHostMesh(enrollment)
            if (mesh.status().state == org.nodehost.core.HostMeshStatus.State.RUNNING) {
                // Record the recovery obligation before erasing the only enrollment key copy.
                phase = phase.copy(phase = EnrollmentPhase.HOST_MESH_ENROLLED_KEY_ERASED)
                phaseStore.save(phase)
                (enrollments as? EncryptedEnrollmentRepository)?.clearConsumedOneTimeCredentials()
                boundaryHook.after(EnrollmentPhase.HOST_MESH_ENROLLED_KEY_ERASED)
            }
        }
        if (phase.phase >= EnrollmentPhase.HOST_MESH_ENROLLED_KEY_ERASED) {
            (enrollments as? EncryptedEnrollmentRepository)?.clearConsumedOneTimeCredentials()
            if (mesh.status().state != org.nodehost.core.HostMeshStatus.State.RUNNING &&
                mesh.status().state != org.nodehost.core.HostMeshStatus.State.ENROLLING
            ) mesh.start() // Durable mesh identity owns restart; the erased one-use key must never be replayed.
            check(bootstrapStore.commit(enrollment.id.value)) { "guest bootstrap commit did not match enrollment authority" }
        }
        wakeReconciler()
        return installed(enrollment, bootstrapProfile?.profile)
    }

    private suspend fun resumeExistingAuthority(enrollment: org.nodehost.model.NodeEnrollment): InstalledNode {
        applyInitialRuntime(enrollment)
        val credentialsRemain = (enrollments as? EncryptedEnrollmentRepository)?.hasOneTimeCredentials() ?: true
        if (credentialsRemain) enrollHostMesh(enrollment)
        else if (mesh.status().state != org.nodehost.core.HostMeshStatus.State.RUNNING &&
            mesh.status().state != org.nodehost.core.HostMeshStatus.State.ENROLLING
        ) mesh.start()
        if (mesh.status().state == org.nodehost.core.HostMeshStatus.State.RUNNING) {
            (enrollments as? EncryptedEnrollmentRepository)?.clearConsumedOneTimeCredentials()
            check(bootstrapStore.commit(enrollment.id.value)) { "guest bootstrap commit did not match enrollment authority" }
        }
        wakeReconciler()
        return installed(enrollment, null)
    }

    private suspend fun applyInitialRuntime(enrollment: org.nodehost.model.NodeEnrollment) {
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
    }

    private suspend fun enrollHostMesh(enrollment: org.nodehost.model.NodeEnrollment) {
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
    }

    private fun installed(enrollment: org.nodehost.model.NodeEnrollment, profile: GuestBootstrapProfile?) = InstalledNode(
        EnrolledControllerAuthenticator(
            enrollment.hostAccess.controllerCapability,
            enrollment.hostAccess.allowedControllerId,
            isControllerRevoked,
        ),
        profile,
    )

    private companion object {
        fun secureToken(bytes: Int): String = ByteArray(bytes).also(SecureRandom()::nextBytes)
            .let { Base64.getUrlEncoder().withoutPadding().encodeToString(it) }
    }
}

private class VolatileEnrollmentPhaseStore : EnrollmentPhaseStore {
    private var state: EnrollmentRecoveryState? = null
    override suspend fun load() = state
    override suspend fun save(state: EnrollmentRecoveryState) { this.state = state }
    override suspend fun clear() { state = null }
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
