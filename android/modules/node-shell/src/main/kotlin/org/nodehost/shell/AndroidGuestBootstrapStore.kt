package org.nodehost.shell

import android.content.Context
import android.util.Base64
import java.io.File
import java.security.MessageDigest
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONObject

/** Keystore-encrypted durable bootstrap state; successful redemption is committed before return. */
class AndroidGuestBootstrapStore(context: Context) : GuestBootstrapStore, BootstrapRequestStore {
    private val application = context.applicationContext
    private val state = AndroidEncryptedBlob(
        application,
        preferencesName = "nodehost_guest_bootstrap_secure_v1",
        preferenceKey = "bootstrap",
        keyAlias = "nodehost.guest.bootstrap.v1",
    )
    private val mutex = Mutex()

    override suspend fun hasDurableState(): Boolean = mutex.withLock { state.read() != null }

    override suspend fun enrollmentId(): String? = mutex.withLock {
        state.read()?.let(::JSONObject)?.optString("enrollmentId")?.takeIf(String::isNotEmpty)
    }

    override suspend fun clear() = mutex.withLock {
        state.clear()
        File(application.filesDir, "vms/default/guest-ready").delete()
        Unit
    }

    override suspend fun commit(enrollmentId: String): Boolean = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock false
        if (value.optString("enrollmentId") != enrollmentId) return@withLock false
        if (!value.optBoolean("committed", true)) {
            value.put("committed", true)
            state.write(value.toString())
        }
        true
    }

    override suspend fun save(materialized: MaterializedGuestBootstrap) = mutex.withLock {
        val existing = state.read()?.let(::JSONObject)
        if (existing != null) {
            require(existing.optString("enrollmentId", materialized.profile.enrollmentId) == materialized.profile.enrollmentId) {
                "a different guest bootstrap enrollment is already staged"
            }
            return@withLock
        }
        val payload = checkNotNull(materialized.secret.persistenceCopy()) { "bootstrap secret was already consumed" }
        val value = JSONObject()
            .put("enrollmentId", materialized.profile.enrollmentId)
            .put("profileId", materialized.profile.profileId)
            .put("token", materialized.profile.token)
            .put("metadataPath", materialized.profile.metadataPath)
            .put("metaData", materialized.profile.metaData)
            .put("userData", materialized.profile.userData)
            .put("secret", Base64.encodeToString(payload, Base64.NO_WRAP))
            .put("callbackCapability", materialized.callbackCapability.value)
            .put("consumed", false)
            .put("committed", false)
            .put("bootGeneration", 0)
            .put("readyGeneration", -1)
        state.write(value.toString())
    }

    override suspend fun beginBoot(profileId: org.nodehost.model.VmProfileId): String? = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock null
        if (!value.optBoolean("committed", true)) return@withLock null
        value.put("profileId", profileId.value)
        value.put("bootGeneration", value.optLong("bootGeneration", 0) + 1)
        state.write(value.toString())
        File(application.filesDir, "vms/default/guest-ready").delete()
        value.getString("token")
    }

    override suspend fun profile(presentedToken: String): GuestBootstrapProfile? = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock null
        if (!value.optBoolean("committed", true) || !sameSecret(value.getString("token"), presentedToken)) return@withLock null
        GuestBootstrapProfile(
            value.optString("enrollmentId", "legacy-enrollment"),
            value.optString("profileId", "ubuntu-2404-arm64-uefi"),
            value.getString("token"), value.getString("metadataPath"),
            value.getString("metaData"), value.getString("userData"),
        )
    }

    override suspend fun vendorData(presentedToken: String): ByteArray? = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock null
        if (!value.optBoolean("committed", true) || !sameSecret(value.getString("token"), presentedToken)) return@withLock null
        when (value.optString("profileId")) {
            "k3s-worker-lab" -> K3S_VENDOR_DATA.toByteArray()
            else -> "#cloud-config\n".toByteArray()
        }
    }

    override suspend fun redeem(presentedToken: String): ByteArray? = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock null
        if (!value.optBoolean("committed", true) || value.getBoolean("consumed") || !sameSecret(value.getString("token"), presentedToken)) return@withLock null
        val payload = Base64.decode(value.getString("secret"), Base64.NO_WRAP)
        require(payload.size in 1..OneUseBootstrapSecret.MAX_SECRET_BYTES)
        value.put("secret", "").put("consumed", true)
        state.write(value.toString())
        payload
    }

    override suspend fun markGuestReady(presentedCapability: String): Boolean = mutex.withLock {
        val value = state.read()?.let(::JSONObject) ?: return@withLock false
        if (!value.optBoolean("committed", true)) return@withLock false
        val callback = value.optString("callbackCapability")
        val accepted = (callback.isNotEmpty() && sameSecret(callback, presentedCapability)) ||
            sameSecret(value.getString("token"), presentedCapability)
        if (!accepted) return@withLock false
        value.remove("callbackCapability")
        value.put("readyGeneration", value.optLong("bootGeneration", 0))
        state.write(value.toString())
        val directory = File(application.filesDir, "vms/default").apply { check(mkdirs() || isDirectory) }
        val temporary = File(directory, "guest-ready.tmp")
        temporary.writeText("generation=${value.optLong("bootGeneration", 0)}\n")
        check(temporary.renameTo(File(directory, "guest-ready"))) { "guest readiness publication failed" }
        true
    }

    private fun sameSecret(expected: String, presented: String): Boolean = MessageDigest.isEqual(
        MessageDigest.getInstance("SHA-256").digest(expected.toByteArray()),
        MessageDigest.getInstance("SHA-256").digest(presented.toByteArray()),
    )

    private companion object {
        val K3S_VENDOR_DATA = """#cloud-config
write_files:
  - path: /usr/local/sbin/nodehost-qualify-k3s
    permissions: '0755'
    content: |
      #!/bin/sh
      set -eu
      install -d -m 0700 /var/lib/nodehost
      checks='cgroup-v2 namespaces overlayfs br-netfilter vxlan tun ip-forwarding'
      printf '{\"profile\":\"k3s-worker-lab\",\"lineage\":\"ubuntu-2404-arm64-uefi\",\"checks\":\"%s\"}\n' "${'$'}checks" > /var/lib/nodehost/k3s-qualification.json
runcmd:
  - [/usr/local/sbin/nodehost-qualify-k3s]
""".trimIndent()
    }
}
