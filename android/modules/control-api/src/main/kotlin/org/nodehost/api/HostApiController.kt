package org.nodehost.api

import java.net.URI
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.ControllerAuthenticator
import org.nodehost.core.ControllerPrincipal
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.OperationRecord
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId

class HostApiConflictException(message: String) : RuntimeException(message)

class HostApiController(
    private val authenticator: ControllerAuthenticator,
    private val queries: HostResourceQueries,
    private val mutations: HostMutationUseCases,
    private val applyRuntime: ApplyRuntimeUseCase,
    private val recoverySsh: RecoverySshGateway,
) {
    suspend fun authorize(header: String?, method: String, path: String): ControllerPrincipal? =
        authenticator.authorize(header, method, path)

    suspend fun status() = queries.status()
    suspend fun capabilities() = queries.capabilities().bounded("capabilities", MAX_CAPABILITIES)
    suspend fun profiles() = queries.profiles().bounded("profiles", MAX_PROFILES)
    suspend fun images() = queries.images().bounded("images", MAX_IMAGES)
    suspend fun vms() = queries.vms().bounded("vms", MAX_VMS)
    suspend fun vm(id: String) = queries.vm(RuntimeId(id))
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
            applyRuntime.apply(spec, key, canonical)
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
        return mutations.removeVm(RuntimeId(id), key, canonical)
    }

    suspend fun cancelOperation(id: String, key: String, canonical: ByteArray): OperationRecord {
        validateIdempotencyKey(key)
        require(OPERATION_ID.matches(id)) { "invalid operation id" }
        return mutations.cancelOperation(id, key, canonical)
    }

    suspend fun revokeController(id: String, key: String, canonical: ByteArray) {
        validateIdempotencyKey(key)
        require(CONTROLLER_ID.matches(id)) { "invalid controller id" }
        mutations.revokeController(id, key, canonical)
    }

    suspend fun openRecovery(vmId: String, principal: ControllerPrincipal): RecoverySshSession =
        recoverySsh.open(RuntimeId(vmId), principal)

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
    fun toRuntimeSpec() = RuntimeSpec(
        id = RuntimeId(id),
        generation = generation,
        desiredState = DesiredRuntimeState.valueOf(desiredState.uppercase()),
        profileId = VmProfileId(profileId),
        memoryMiB = memoryMiB,
        vcpus = vcpus,
        dataDiskGiB = dataDiskGiB,
        preserveDataOnDelete = preserveOnDelete,
    )
}
