package org.nodehost.shell

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.math.BigInteger
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.SecureRandom
import java.util.Date
import javax.security.auth.x500.X500Principal
import org.nodehost.api.TlsServerCredentials

/** Device-local TLS identity. Private key material is generated and remains non-exportable in Android Keystore. */
object AndroidTlsCredentials {
    private const val ALIAS = "nodehost.host-api.tls.v1"

    fun loadOrCreate(nowEpochMillis: Long = System.currentTimeMillis()): TlsServerCredentials {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        if (!keyStore.containsAlias(ALIAS)) {
            val serial = BigInteger(160, SecureRandom()).abs().max(BigInteger.ONE)
            val notBefore = Date(nowEpochMillis - 24L * 60 * 60 * 1000)
            val notAfter = Date(nowEpochMillis + 10L * 365 * 24 * 60 * 60 * 1000)
            KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore").run {
                initialize(
                    KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY)
                        .setAlgorithmParameterSpec(java.security.spec.ECGenParameterSpec("secp256r1"))
                        .setDigests(KeyProperties.DIGEST_SHA256)
                        .setCertificateSubject(X500Principal("CN=NodeHost Host API"))
                        .setCertificateSerialNumber(serial)
                        .setCertificateNotBefore(notBefore)
                        .setCertificateNotAfter(notAfter)
                        .setUserAuthenticationRequired(false)
                        .build(),
                )
                generateKeyPair()
            }
        }
        check(keyStore.isKeyEntry(ALIAS)) { "Host API TLS key is unavailable" }
        return TlsServerCredentials(keyStore, ALIAS, CharArray(0), CharArray(0))
    }
}
