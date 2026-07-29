package org.nodehost.mesh

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import org.json.JSONObject

/** App-private AES-GCM state whose non-exportable key is held by Android Keystore. */
internal class AndroidSecureState(context: Context) {
    private val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
    private val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    @Synchronized
    fun put(name: String, value: String) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val ciphertext = cipher.doFinal(value.toByteArray(StandardCharsets.UTF_8))
        val encoded = Base64.encodeToString(cipher.iv + ciphertext, Base64.NO_WRAP)
        check(preferences.edit().putString(name, encoded).commit()) { "encrypted state write failed" }
    }

    @Synchronized
    fun get(name: String): String? {
        val encoded = preferences.getString(name, null) ?: return null
        val payload = Base64.decode(encoded, Base64.NO_WRAP)
        require(payload.size > GCM_IV_BYTES) { "invalid encrypted state" }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            secretKey(),
            GCMParameterSpec(GCM_TAG_BITS, payload.copyOfRange(0, GCM_IV_BYTES)),
        )
        return String(cipher.doFinal(payload.copyOfRange(GCM_IV_BYTES, payload.size)), StandardCharsets.UTF_8)
    }

    @Synchronized
    fun remove(name: String) {
        check(preferences.edit().remove(name).commit()) { "encrypted state deletion failed" }
    }

    @Synchronized
    fun names(prefix: String): List<String> = preferences.all.keys
        .asSequence()
        .filter { it.startsWith(prefix) }
        .take(MAX_STATE_KEYS)
        .toList()

    @Synchronized
    fun clearNames(names: Collection<String>) {
        require(names.size <= MAX_STATE_KEYS)
        val editor = preferences.edit()
        names.forEach(editor::remove)
        check(editor.commit()) { "encrypted state deletion failed" }
    }

    private fun secretKey(): SecretKey {
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val PREFERENCES_NAME = "nodehost_mesh_secure_state_v1"
        const val KEY_ALIAS = "nodehost.mesh.state.v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val GCM_IV_BYTES = 12
        const val GCM_TAG_BITS = 128
        const val MAX_STATE_KEYS = 256
    }
}

internal class AndroidMeshConfigurationStore(context: Context) : MeshConfigurationStore {
    private val state = AndroidSecureState(context)

    override suspend fun save(configuration: PersistedMeshConfiguration) = write(configuration)

    override suspend fun load(): PersistedMeshConfiguration? {
        val json = state.get(CONFIGURATION) ?: return null
        val value = JSONObject(json)
        return PersistedMeshConfiguration(
            value.getString("controlUrl"),
            value.getString("hostname"),
            value.optString("oneUseAuthKey").ifEmpty { null },
        )
    }

    override suspend fun deleteOneUseAuthKey() {
        val current = load() ?: return
        if (current.oneUseAuthKey != null) write(current.copy(oneUseAuthKey = null))
    }

    override suspend fun clear() = state.remove(CONFIGURATION)

    private fun write(configuration: PersistedMeshConfiguration) {
        val value = JSONObject()
            .put("controlUrl", configuration.controlUrl)
            .put("hostname", configuration.hostname)
        configuration.oneUseAuthKey?.let { value.put("oneUseAuthKey", it) }
        state.put(CONFIGURATION, value.toString())
    }

    private companion object {
        const val CONFIGURATION = "config.v1"
    }
}
