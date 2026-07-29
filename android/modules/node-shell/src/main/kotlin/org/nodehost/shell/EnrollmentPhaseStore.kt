package org.nodehost.shell

import android.content.Context
import android.util.Base64
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONObject

internal enum class EnrollmentPhase {
    VALIDATED_STAGED,
    AUTHORITY_ACCEPTED,
    INITIAL_RUNTIME_ACCEPTED,
    HOST_MESH_ENROLLED_KEY_ERASED,
    BOOTSTRAP_COMMITTED_API_READY,
}

internal data class EnrollmentRecoveryState(
    val enrollmentId: String,
    val phase: EnrollmentPhase,
    val rawEnrollment: ByteArray,
    val rawGuestBootstrapSecret: ByteArray,
    val idempotencyKey: String,
    val requestDigest: String,
    val approvedIssuerSpkiSha256: String,
)

internal interface EnrollmentPhaseStore {
    suspend fun load(): EnrollmentRecoveryState?
    suspend fun save(state: EnrollmentRecoveryState)
    suspend fun clear()
}

/** Encrypted app-private enrollment transaction state used only until all external boundaries converge. */
internal class AndroidEnrollmentPhaseStore(context: Context) : EnrollmentPhaseStore {
    private val blob = AndroidEncryptedBlob(
        context.applicationContext,
        preferencesName = "nodehost_enrollment_phase_secure_v1",
        preferenceKey = "phase",
        keyAlias = "nodehost.enrollment.phase.v1",
        maxPlaintextBytes = MAX_PHASE_BYTES,
    )
    private val mutex = Mutex()

    override suspend fun load(): EnrollmentRecoveryState? = mutex.withLock {
        blob.read()?.let(::decode)
    }

    override suspend fun save(state: EnrollmentRecoveryState) = mutex.withLock {
        require(state.rawEnrollment.size <= EnrollmentJson.MAX_ENROLLMENT_BYTES)
        require(state.rawGuestBootstrapSecret.size <= OneUseBootstrapSecret.MAX_SECRET_BYTES)
        blob.write(JSONObject()
            .put("version", 1)
            .put("enrollmentId", state.enrollmentId)
            .put("phase", state.phase.name)
            .put("rawEnrollment", Base64.encodeToString(state.rawEnrollment, Base64.NO_WRAP))
            .put("rawGuestBootstrapSecret", Base64.encodeToString(state.rawGuestBootstrapSecret, Base64.NO_WRAP))
            .put("idempotencyKey", state.idempotencyKey)
            .put("requestDigest", state.requestDigest)
            .put("approvedIssuerSpkiSha256", state.approvedIssuerSpkiSha256)
            .toString())
    }

    override suspend fun clear() = mutex.withLock { blob.clear() }

    private fun decode(raw: String): EnrollmentRecoveryState {
        val value = JSONObject(raw)
        require(value.keys().asSequence().toSet() == setOf(
            "version", "enrollmentId", "phase", "rawEnrollment", "rawGuestBootstrapSecret",
            "idempotencyKey", "requestDigest", "approvedIssuerSpkiSha256",
        )) { "invalid enrollment recovery fields" }
        require(value.getInt("version") == 1) { "unsupported enrollment recovery version" }
        return EnrollmentRecoveryState(
            value.getString("enrollmentId"),
            EnrollmentPhase.valueOf(value.getString("phase")),
            Base64.decode(value.getString("rawEnrollment"), Base64.NO_WRAP),
            Base64.decode(value.getString("rawGuestBootstrapSecret"), Base64.NO_WRAP),
            value.getString("idempotencyKey"),
            value.getString("requestDigest"),
            value.getString("approvedIssuerSpkiSha256"),
        ).also {
            require(it.rawEnrollment.size <= EnrollmentJson.MAX_ENROLLMENT_BYTES)
            require(it.rawGuestBootstrapSecret.size <= OneUseBootstrapSecret.MAX_SECRET_BYTES)
            if (it.phase == EnrollmentPhase.VALIDATED_STAGED) {
                require(it.rawEnrollment.isNotEmpty() && it.rawGuestBootstrapSecret.isNotEmpty())
            }
            require(it.idempotencyKey.length in 16..200)
            require(it.requestDigest.matches(Regex("[a-f0-9]{64}")))
        }
    }

    private companion object {
        const val MAX_PHASE_BYTES = 1_500_000
    }
}
