package org.nodehost.shell

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject
import org.nodehost.core.EnrollmentAcceptance
import org.nodehost.core.EnrollmentRepository
import org.nodehost.model.ArtifactDefaults
import org.nodehost.model.ControllerEnrollment
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.EnrollmentId
import org.nodehost.model.GuestAccessEnrollment
import org.nodehost.model.GuestSshAuthorization
import org.nodehost.model.HostAccessEnrollment
import org.nodehost.model.HostMeshEnrollment
import org.nodehost.model.InitialRuntimeDefaults
import org.nodehost.model.NodeEnrollment
import org.nodehost.model.NodeName
import org.nodehost.model.OperationId
import org.nodehost.model.OperationRecord
import org.nodehost.model.OperationState
import org.nodehost.model.SensitiveValue
import org.nodehost.model.VmProfileId

/** Enrollment and its idempotency record are one encrypted, atomically committed authority blob. */
class EncryptedEnrollmentRepository(context: Context) : EnrollmentRepository {
    private val state = AndroidEncryptedBlob(
        context.applicationContext,
        preferencesName = "nodehost_enrollment_secure_v1",
        preferenceKey = "authority",
        keyAlias = "nodehost.enrollment.authority.v1",
    )
    private val mutex = Mutex()

    override suspend fun load(): NodeEnrollment? = mutex.withLock { state.read()?.let(EnrollmentJson::decodeStored)?.first }

    override suspend fun acceptEnrollment(
        enrollment: NodeEnrollment,
        operation: OperationRecord,
    ): EnrollmentAcceptance = mutex.withLock {
        val current = state.read()?.let(EnrollmentJson::decodeStored)
        if (current != null) {
            val (_, existingOperation) = current
            if (existingOperation.idempotencyKey == operation.idempotencyKey) {
                return@withLock if (existingOperation.requestDigest == operation.requestDigest) {
                    EnrollmentAcceptance.Replay(existingOperation)
                } else EnrollmentAcceptance.IdempotencyConflict
            }
            return@withLock EnrollmentAcceptance.EnrollmentConflict
        }
        state.write(EnrollmentJson.encodeStored(enrollment, operation))
        EnrollmentAcceptance.Accepted
    }
}

/** Strict boundary parser for the versioned public enrollment contract. */
object EnrollmentJson {
    const val MAX_ENROLLMENT_BYTES = 256 * 1024

    fun parse(raw: ByteArray): NodeEnrollment {
        require(raw.isNotEmpty() && raw.size <= MAX_ENROLLMENT_BYTES) { "enrollment is empty or too large" }
        val root = JSONObject(raw.toString(Charsets.UTF_8)).keysExactly(
            "apiVersion", "kind", "metadata", "controller", "hostMesh", "hostAccess", "guestAccess", "artifacts", "initialRuntime",
        )
        require(root.string("apiVersion") == "nodehost.example/v1alpha1") { "unsupported enrollment apiVersion" }
        require(root.string("kind") == "NodeEnrollment") { "unsupported enrollment kind" }
        val metadata = root.objectValue("metadata").keysExactly("enrollmentId", "nodeName", "expiresAt")
        val controller = root.objectValue("controller").keysExactly("endpoint", "spkiSha256", "oneTimeEnrollmentToken")
        val hostMesh = root.objectValue("hostMesh").keysExactly("controlUrl", "oneUseAuthKey", "hostname", "expectedTags")
        val hostAccess = root.objectValue("hostAccess").keysExactly("controllerCapability", "allowedControllerId")
        val guestAccess = root.objectValue("guestAccess")
        val guestKeys = guestAccess.keysAsSet()
        require(guestKeys == setOf("sshUser", "sshUserCaPublicKey") || guestKeys == setOf("sshUser", "emergencyAuthorizedKeys")) {
            "guestAccess must contain exactly one SSH authorization form"
        }
        val artifacts = root.objectValue("artifacts").keysExactly("repositoryUrl", "profileIds")
        val initial = root.objectValue("initialRuntime").keysExactly("profileId", "desiredState", "memoryMiB", "vcpus", "dataDiskGiB")
        val authorization = if (guestAccess.has("sshUserCaPublicKey")) {
            GuestSshAuthorization.UserCertificateAuthority(guestAccess.string("sshUserCaPublicKey"))
        } else {
            GuestSshAuthorization.AuthorizedKeys(guestAccess.stringSet("emergencyAuthorizedKeys", 4))
        }
        return NodeEnrollment(
            EnrollmentId(metadata.string("enrollmentId")),
            NodeName(metadata.string("nodeName")),
            java.time.Instant.parse(metadata.string("expiresAt")).toEpochMilli(),
            ControllerEnrollment(controller.string("endpoint"), controller.string("spkiSha256"), SensitiveValue(controller.string("oneTimeEnrollmentToken"))),
            HostMeshEnrollment(hostMesh.string("controlUrl"), SensitiveValue(hostMesh.string("oneUseAuthKey")), NodeName(hostMesh.string("hostname")), hostMesh.stringSet("expectedTags", 8)),
            HostAccessEnrollment(SensitiveValue(hostAccess.string("controllerCapability")), hostAccess.string("allowedControllerId")),
            GuestAccessEnrollment(guestAccess.string("sshUser"), authorization),
            ArtifactDefaults(artifacts.string("repositoryUrl"), artifacts.stringSet("profileIds", 16).map(::VmProfileId).toSet()),
            InitialRuntimeDefaults(
                VmProfileId(initial.string("profileId")),
                DesiredRuntimeState.valueOf(initial.string("desiredState").uppercase()),
                initial.intValue("memoryMiB"), initial.intValue("vcpus"), initial.intValue("dataDiskGiB"),
            ),
        )
    }

    internal fun encodeStored(enrollment: NodeEnrollment, operation: OperationRecord): String = JSONObject()
        .put("enrollment", encodeEnrollment(enrollment))
        .put("operation", JSONObject()
            .put("id", operation.id.value)
            .put("key", operation.idempotencyKey)
            .put("digest", operation.requestDigest)
            .put("state", operation.state.name))
        .toString()

    internal fun decodeStored(raw: String): Pair<NodeEnrollment, OperationRecord> {
        val root = JSONObject(raw).keysExactly("enrollment", "operation")
        val enrollmentRaw = root.objectValue("enrollment").toString().toByteArray()
        val operation = root.objectValue("operation").keysExactly("id", "key", "digest", "state")
        return parse(enrollmentRaw) to OperationRecord(
            OperationId(operation.string("id")), operation.string("key"), operation.string("digest"),
            null, null, OperationState.valueOf(operation.string("state")), null,
        )
    }

    private fun encodeEnrollment(value: NodeEnrollment): JSONObject {
        val guest = JSONObject().put("sshUser", value.guestAccess.sshUser)
        when (val authorization = value.guestAccess.authorization) {
            is GuestSshAuthorization.UserCertificateAuthority -> guest.put("sshUserCaPublicKey", authorization.publicKey)
            is GuestSshAuthorization.AuthorizedKeys -> guest.put("emergencyAuthorizedKeys", JSONArray(authorization.publicKeys.sorted()))
        }
        return JSONObject()
            .put("apiVersion", "nodehost.example/v1alpha1").put("kind", "NodeEnrollment")
            .put("metadata", JSONObject().put("enrollmentId", value.id.value).put("nodeName", value.nodeName.value).put("expiresAt", java.time.Instant.ofEpochMilli(value.expiresAtEpochMs).toString()))
            .put("controller", JSONObject().put("endpoint", value.controller.endpoint).put("spkiSha256", value.controller.spkiSha256).put("oneTimeEnrollmentToken", value.controller.oneTimeEnrollmentToken.value))
            .put("hostMesh", JSONObject().put("controlUrl", value.hostMesh.controlUrl).put("oneUseAuthKey", value.hostMesh.oneUseAuthKey.value).put("hostname", value.hostMesh.hostname.value).put("expectedTags", JSONArray(value.hostMesh.expectedTags.sorted())))
            .put("hostAccess", JSONObject().put("controllerCapability", value.hostAccess.controllerCapability.value).put("allowedControllerId", value.hostAccess.allowedControllerId))
            .put("guestAccess", guest)
            .put("artifacts", JSONObject().put("repositoryUrl", value.artifacts.repositoryUrl).put("profileIds", JSONArray(value.artifacts.profileIds.map { it.value }.sorted())))
            .put("initialRuntime", JSONObject().put("profileId", value.initialRuntime.profileId.value).put("desiredState", value.initialRuntime.desiredState.name.lowercase()).put("memoryMiB", value.initialRuntime.memoryMiB).put("vcpus", value.initialRuntime.vcpus).put("dataDiskGiB", value.initialRuntime.dataDiskGiB))
    }

    private fun JSONObject.keysExactly(vararg expected: String): JSONObject = apply {
        require(keysAsSet() == expected.toSet()) { "invalid fields" }
    }
    private fun JSONObject.keysAsSet(): Set<String> = buildSet {
        val iterator = keys()
        while (iterator.hasNext()) add(iterator.next())
    }
    private fun JSONObject.objectValue(name: String): JSONObject = get(name).let { require(it is JSONObject) { "$name must be an object" }; it }
    private fun JSONObject.string(name: String): String = get(name).let { require(it is String && it.isNotEmpty()) { "$name must be a string" }; it }
    private fun JSONObject.intValue(name: String): Int = get(name).let { require(it is Int) { "$name must be an integer" }; it }
    private fun JSONObject.stringSet(name: String, maximum: Int): Set<String> {
        val array = get(name)
        require(array is JSONArray && array.length() in 1..maximum) { "$name is out of range" }
        val values = buildSet { for (index in 0 until array.length()) add(array.get(index).also { require(it is String) } as String) }
        require(values.size == array.length()) { "$name contains duplicates" }
        return values
    }
}

internal class AndroidEncryptedBlob(
    context: Context,
    private val preferencesName: String,
    private val preferenceKey: String,
    private val keyAlias: String,
) {
    private val preferences = context.getSharedPreferences(preferencesName, Context.MODE_PRIVATE)
    private val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    @Synchronized fun read(): String? {
        val encoded = preferences.getString(preferenceKey, null) ?: return null
        val bytes = Base64.decode(encoded, Base64.NO_WRAP)
        require(bytes.size > IV_BYTES) { "invalid encrypted enrollment" }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, IV_BYTES)))
        return String(cipher.doFinal(bytes.copyOfRange(IV_BYTES, bytes.size)), Charsets.UTF_8)
    }

    @Synchronized fun write(value: String) {
        require(value.toByteArray().size <= EnrollmentJson.MAX_ENROLLMENT_BYTES + 4096)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encoded = Base64.encodeToString(cipher.iv + cipher.doFinal(value.toByteArray()), Base64.NO_WRAP)
        check(preferences.edit().putString(preferenceKey, encoded).commit()) { "encrypted state commit failed" }
    }

    private fun key(): SecretKey {
        (keyStore.getKey(keyAlias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder(keyAlias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setKeySize(256).build())
            generateKey()
        }
    }

    private companion object {
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_BYTES = 12
    }
}
