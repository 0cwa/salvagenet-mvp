package org.nodehost.shell

import android.content.Context
import android.util.Base64
import java.io.File
import java.security.MessageDigest
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONObject

/** Keystore-encrypted durable bootstrap state; successful redemption is committed before return. */
class AndroidGuestBootstrapStore(context: Context) : GuestBootstrapStore {
    private val application = context.applicationContext
    private val state = AndroidEncryptedBlob(
        application,
        preferencesName = "nodehost_guest_bootstrap_secure_v1",
        preferenceKey = "bootstrap",
        keyAlias = "nodehost.guest.bootstrap.v1",
    )
    private val mutex = Mutex()

    override suspend fun hasDurableState(): Boolean = mutex.withLock { state.read() != null }

    override suspend fun save(materialized: MaterializedGuestBootstrap) = mutex.withLock {
        val existing = state.read()?.let(::JSONObject)
        if (existing != null && existing.getString("token") == materialized.profile.token) return@withLock
        val payload = checkNotNull(materialized.secret.persistenceCopy()) { "bootstrap secret was already consumed" }
        val value = JSONObject()
            .put("token", materialized.profile.token)
            .put("metadataPath", materialized.profile.metadataPath)
            .put("metaData", materialized.profile.metaData)
            .put("userData", materialized.profile.userData)
            .put("secret", Base64.encodeToString(payload, Base64.NO_WRAP))
            .put("callbackCapability", materialized.callbackCapability.value)
            .put("consumed", false)
        state.write(value.toString())
    }

    suspend fun bootstrapToken(): String? = mutex.withLock {
        state.read()?.let(::JSONObject)?.takeUnless { it.getBoolean("consumed") }?.getString("token")
    }

    suspend fun profile(presentedToken: String): GuestBootstrapProfile? = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock null
        if (value.getBoolean("consumed") || !sameSecret(value.getString("token"), presentedToken)) return@withLock null
        GuestBootstrapProfile(
            value.getString("token"), value.getString("metadataPath"),
            value.getString("metaData"), value.getString("userData"),
        )
    }

    suspend fun redeem(presentedToken: String): ByteArray? = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock null
        if (value.getBoolean("consumed") || !sameSecret(value.getString("token"), presentedToken)) return@withLock null
        val payload = Base64.decode(value.getString("secret"), Base64.NO_WRAP)
        require(payload.size in 1..OneUseBootstrapSecret.MAX_SECRET_BYTES)
        value.put("secret", "").put("consumed", true)
        state.write(value.toString())
        payload
    }

    suspend fun markGuestReady(presentedCapability: String): Boolean = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock false
        if (!sameSecret(value.getString("callbackCapability"), presentedCapability)) return@withLock false
        value.put("callbackCapability", "consumed")
        state.write(value.toString())
        val directory = File(application.filesDir, "vms/default").apply { check(mkdirs() || isDirectory) }
        val temporary = File(directory, "guest-ready.tmp")
        temporary.writeText("ready\n")
        check(temporary.renameTo(File(directory, "guest-ready"))) { "guest readiness publication failed" }
        true
    }

    private fun sameSecret(expected: String, presented: String): Boolean = MessageDigest.isEqual(
        MessageDigest.getInstance("SHA-256").digest(expected.toByteArray()),
        MessageDigest.getInstance("SHA-256").digest(presented.toByteArray()),
    )
}
