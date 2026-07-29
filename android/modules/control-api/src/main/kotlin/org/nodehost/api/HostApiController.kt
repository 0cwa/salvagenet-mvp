package org.nodehost.api

import java.net.URI
import java.util.ArrayDeque
import java.util.concurrent.atomic.AtomicBoolean
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.ControllerAuthenticator
import org.nodehost.core.ControllerPrincipal
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.OperationRecord
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId

class HostApiConflictException(message: String) : RuntimeException(message)
class HostApiRateLimitException(message: String) : RuntimeException(message)

class HostApiController(
    private val authenticator: ControllerAuthenticator,
    private val queries: HostResourceQueries,
    private val mutations: HostMutationUseCases,
    private val applyRuntime: ApplyRuntimeUseCase,
    private val recoverySsh: RecoverySshGateway,
    private val acceptedOperationDispatcher: AcceptedOperationDispatcher = AcceptedOperationDispatcher.UNCONFIGURED,
    monotonicNanos: () -> Long = System::nanoTime,
    recoveryMaxStartsPerMinute: Int = RECOVERY_MAX_STARTS_PER_MINUTE,
) {
    private val recoveryAdmission = RecoveryAdmission(monotonicNanos, recoveryMaxStartsPerMinute)

    suspend fun authorize(header: String?, method: String, path: String): ControllerPrincipal? =
        authenticator.authorize(header, method, path)

    suspend fun status() = queries.status()
    suspend fun capabilities() = queries.capabilities().bounded("capabilities", MAX_CAPABILITIES)
    suspend fun profiles() = queries.profiles().bounded("profiles", MAX_PROFILES)
    suspend fun images() = queries.images().bounded("images", MAX_IMAGES)
    suspend fun vms() = queries.vms().bounded("vms", MAX_VMS).also { values ->
        require(values.all { it.id == RuntimeId.DEFAULT.value }) { "MVP supports only the default runtime" }
    }
    suspend fun vm(id: String) = queries.vm(defaultRuntimeId(id))
    suspend fun operations() = queries.operations().bounded("operations", MAX_OPERATIONS)
    suspend fun operation(id: String): OperationRecord? {
        require(OPERATION_ID.matches(id)) { "invalid operation id" }
        return queries.operation(id)
    }
    suspend fun diagnostics(): HostDiagnostics {
        val result = queries.diagnostics()
        require(result.entries.size <= MAX_DIAGNOSTIC_ENTRIES) { "diagnostics exceeded resource bound" }
        require(result.entries.all { (key, value) ->
            DIAGNOSTIC_KEY.matches(key) && value.length <= 512 &&
                SENSITIVE_DIAGNOSTIC_WORDS.none { key.contains(it, ignoreCase = true) }
        }) { "diagnostics entry exceeded resource or redaction bound" }
        return result
    }

    suspend fun importImage(request: ImageImportRequest, key: String, canonical: ByteArray): OperationRecord {
        validateIdempotencyKey(key)
        val uri = URI(request.sourceUrl)
        require(uri.scheme == "https" && uri.host != null && uri.userInfo == null && uri.fragment == null) {
            "sourceUrl must be an HTTPS URL without credentials or fragment"
        }
        require(request.sourceUrl.length <= 2048) { "sourceUrl is too long" }
        require(SHA256.matches(request.sha256)) { "invalid sha256" }
        require(request.expectedSizeBytes in 1..MAX_IMAGE_BYTES) { "expectedSizeBytes is out of range" }
        return mutations.importImage(request, key, canonical)
    }

    suspend fun applyVm(request: ApplyVmRequest, key: String, canonical: ByteArray): OperationRecord {
        validateIdempotencyKey(key)
        val spec = request.toRuntimeSpec()
        return try {
            applyRuntime.apply(spec, key, canonical).also { acceptedOperationDispatcher.dispatch(it) }
        } catch (failure: IllegalArgumentException) {
            val message = failure.message.orEmpty()
            if (message.startsWith("idempotency key reused") || message.startsWith("generation rejected")) {
                throw HostApiConflictException(message)
            }
            throw failure
        }
    }

    suspend fun removeVm(id: String, key: String, canonical: ByteArray): OperationRecord {
        validateIdempotencyKey(key)
        return mutations.removeVm(defaultRuntimeId(id), key, canonical)
            .also { acceptedOperationDispatcher.dispatch(it) }
    }

    suspend fun cancelOperation(id: String, key: String, canonical: ByteArray): OperationRecord {
        validateIdempotencyKey(key)
        require(OPERATION_ID.matches(id)) { "invalid operation id" }
        return mutations.cancelOperation(id, key, canonical)
            .also { acceptedOperationDispatcher.dispatch(it) }
    }

    suspend fun revokeController(id: String, key: String, canonical: ByteArray) {
        validateIdempotencyKey(key)
        require(CONTROLLER_ID.matches(id)) { "invalid controller id" }
        mutations.revokeController(id, key, canonical)
    }

    suspend fun openRecovery(vmId: String, principal: ControllerPrincipal): RecoverySshSession {
        val runtimeId = defaultRuntimeId(vmId)
        val lease = recoveryAdmission.acquire()
        return try {
            AdmissionRecoverySshSession(recoverySsh.open(runtimeId, principal), lease)
        } catch (failure: Throwable) {
            lease.close()
            throw failure
        }
    }

    private fun defaultRuntimeId(raw: String): RuntimeId {
        val id = RuntimeId(raw)
        require(id == RuntimeId.DEFAULT) { "MVP supports only the default runtime" }
        return id
    }

    private fun <T> List<T>.bounded(name: String, maximum: Int): List<T> {
        require(size <= maximum) { "$name exceeded resource bound" }
        return this
    }

    private fun validateIdempotencyKey(key: String) {
        require(key.length in 16..200 && key.all { it.code in 0x21..0x7e }) { "invalid idempotency key" }
    }

    companion object {
        const val MAX_REQUEST_BYTES = 1_048_576
        const val MAX_IMAGE_BYTES = 64L * 1024 * 1024 * 1024
        const val MAX_CAPABILITIES = 128
        const val MAX_PROFILES = 32
        const val MAX_IMAGES = 128
        const val MAX_VMS = 1
        const val MAX_OPERATIONS = 256
        const val MAX_DIAGNOSTIC_ENTRIES = 128
        const val RECOVERY_MAX_STARTS_PER_MINUTE = 6
        val OPERATION_ID = Regex("[A-Za-z0-9][A-Za-z0-9._-]{2,127}")
        val CONTROLLER_ID = Regex("[A-Za-z0-9][A-Za-z0-9._-]{2,127}")
        val SHA256 = Regex("[a-f0-9]{64}")
        val DIAGNOSTIC_KEY = Regex("[a-z][a-z0-9_.-]{0,63}")
        val SENSITIVE_DIAGNOSTIC_WORDS = setOf("authorization", "credential", "password", "secret", "token", "capability")
    }
}

data class ApplyVmRequest(
    val id: String,
    val generation: Long,
    val desiredState: String,
    val profileId: String,
    val memoryMiB: Int,
    val vcpus: Int,
    val dataDiskGiB: Int,
    val preserveOnDelete: Boolean,
) {
    fun toRuntimeSpec(): RuntimeSpec {
        require(RuntimeId(id) == RuntimeId.DEFAULT) { "MVP supports only the default runtime" }
        return RuntimeSpec(
            id = RuntimeId.DEFAULT,
            generation = generation,
            desiredState = DesiredRuntimeState.valueOf(desiredState.uppercase()),
            profileId = VmProfileId(profileId),
            memoryMiB = memoryMiB,
            vcpus = vcpus,
            dataDiskGiB = dataDiskGiB,
            preserveDataOnDelete = preserveOnDelete,
        )
    }
}

private class RecoveryAdmission(
    private val monotonicNanos: () -> Long,
    private val maxStartsPerMinute: Int,
) {
    private val active = AtomicBoolean(false)
    private val starts = ArrayDeque<Long>()

    init { require(maxStartsPerMinute in 1..60) }

    fun acquire(): AutoCloseable {
        val now = monotonicNanos()
        synchronized(starts) {
            val cutoff = now - ONE_MINUTE_NANOS
            while (starts.isNotEmpty() && starts.first() <= cutoff) starts.removeFirst()
            if (starts.size >= maxStartsPerMinute) throw HostApiRateLimitException("recovery SSH start rate exceeded")
            if (!active.compareAndSet(false, true)) throw HostApiConflictException("a recovery SSH session is already active")
            starts.addLast(now)
        }
        return AutoCloseable { active.set(false) }
    }

    companion object { private const val ONE_MINUTE_NANOS = 60_000_000_000L }
}

private class AdmissionRecoverySshSession(
    private val delegate: RecoverySshSession,
    private val lease: AutoCloseable,
) : RecoverySshSession {
    private val closed = AtomicBoolean(false)
    override suspend fun read(maxBytes: Int): ByteArray? = delegate.read(maxBytes)
    override suspend fun write(bytes: ByteArray) = delegate.write(bytes)
    override suspend fun close() {
        if (closed.compareAndSet(false, true)) {
            try { delegate.close() } finally { lease.close() }
        }
    }
}
