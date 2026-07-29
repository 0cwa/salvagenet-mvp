package org.nodehost.shell

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.io.ByteArrayInputStream
import java.math.BigInteger
import java.net.InetAddress
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.PublicKey
import java.security.SecureRandom
import java.security.Signature
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Base64
import java.util.Date
import javax.security.auth.x500.X500Principal
import org.nodehost.api.TlsServerCredentials

/** Device-local TLS identity. Private key material is generated and remains non-exportable in Android Keystore. */
object AndroidTlsCredentials {
    private const val ALIAS = "nodehost.host-api.tls.v1"

    fun loadOrCreate(tailnetAddress: String? = null, nowEpochMillis: Long = System.currentTimeMillis()): TlsServerCredentials {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        if (!keyStore.containsAlias(ALIAS)) {
            val serial = BigInteger(160, SecureRandom()).abs().max(BigInteger.ONE)
            val notBefore = Date(nowEpochMillis - DAY_MILLIS)
            val notAfter = Date(nowEpochMillis + 10L * 365 * DAY_MILLIS)
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
        if (tailnetAddress != null) installAddressCertificate(keyStore, tailnetAddress, nowEpochMillis)
        return TlsServerCredentials(keyStore, ALIAS, CharArray(0), CharArray(0))
    }

    private fun installAddressCertificate(keyStore: KeyStore, tailnetAddress: String, nowEpochMillis: Long) {
        require(IPV4.matches(tailnetAddress) || tailnetAddress.contains(':')) { "TLS SAN requires a literal tailnet address" }
        val address = InetAddress.getByName(tailnetAddress)
        require(tailnetAddress.removePrefix("[").removeSuffix("]") == address.hostAddress) { "TLS SAN requires a canonical literal tailnet address" }
        val current = keyStore.getCertificate(ALIAS) as X509Certificate
        val alreadyInstalled = current.subjectAlternativeNames.orEmpty().any { entry ->
            entry.size >= 2 && entry[0] == 7 && runCatching { InetAddress.getByName(entry[1].toString()) == address }.getOrDefault(false)
        }
        if (alreadyInstalled) return
        val privateKey = keyStore.getKey(ALIAS, null) as PrivateKey
        val certificate = addressCertificate(privateKey, current.publicKey, address, nowEpochMillis)
        keyStore.setEntry(ALIAS, KeyStore.PrivateKeyEntry(privateKey, arrayOf(certificate)), null)
    }

    /** Small bounded X.509 builder used because Android KeyGenParameterSpec cannot request a SAN. */
    internal fun addressCertificate(
        privateKey: PrivateKey,
        publicKey: PublicKey,
        address: InetAddress,
        nowEpochMillis: Long,
    ): X509Certificate {
        val signatureAlgorithm = derSequence(derOid("1.2.840.10045.4.3.2"))
        val name = derSequence(derSet(derSequence(derOid("2.5.4.3"), der(0x0c, "NodeHost Host API".toByteArray()))))
        val validity = derSequence(
            derGeneralizedTime(nowEpochMillis - DAY_MILLIS),
            derGeneralizedTime(nowEpochMillis + 10L * 365 * DAY_MILLIS),
        )
        val san = derSequence(der(0x87, address.address))
        val extensions = der(0xa3, derSequence(derSequence(derOid("2.5.29.17"), der(0x04, san))))
        val tbs = derSequence(
            der(0xa0, derInteger(BigInteger.valueOf(2))),
            derInteger(BigInteger(160, SecureRandom()).abs().max(BigInteger.ONE)),
            signatureAlgorithm,
            name,
            validity,
            name,
            publicKey.encoded,
            extensions,
        )
        val signature = Signature.getInstance("SHA256withECDSA").run { initSign(privateKey); update(tbs); sign() }
        val encoded = derSequence(tbs, signatureAlgorithm, der(0x03, byteArrayOf(0) + signature))
        return (CertificateFactory.getInstance("X.509").generateCertificate(ByteArrayInputStream(encoded)) as X509Certificate).also {
            check(it.tbsCertificate.contentEquals(tbs)) { "certificate encoder changed signed content" }
        }
    }

    fun clear() {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        if (keyStore.containsAlias(ALIAS)) keyStore.deleteEntry(ALIAS)
    }

    /** Public trust anchor shown/exported only after the enrollment confirmation step. */
    fun spkiSha256(): String {
        loadOrCreate()
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        return MessageDigest.getInstance("SHA-256").digest(keyStore.getCertificate(ALIAS).publicKey.encoded)
            .joinToString("") { "%02x".format(it) }
    }

    fun certificatePem(): ByteArray {
        loadOrCreate()
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val encoded = Base64.getMimeEncoder(64, "\n".toByteArray()).encodeToString(keyStore.getCertificate(ALIAS).encoded)
        return "-----BEGIN CERTIFICATE-----\n$encoded\n-----END CERTIFICATE-----\n".toByteArray()
    }

    private fun derSequence(vararg values: ByteArray) = der(0x30, values.fold(ByteArray(0), ByteArray::plus))
    private fun derSet(vararg values: ByteArray) = der(0x31, values.fold(ByteArray(0), ByteArray::plus))
    private fun derInteger(value: BigInteger) = der(0x02, value.toByteArray())
    private fun derGeneralizedTime(epochMillis: Long) = der(
        0x18,
        DateTimeFormatter.ofPattern("yyyyMMddHHmmss'Z'").withZone(ZoneOffset.UTC).format(Instant.ofEpochMilli(epochMillis)).toByteArray(),
    )
    private fun derOid(value: String): ByteArray {
        val parts = value.split('.').map(String::toLong)
        val bytes = mutableListOf((parts[0] * 40 + parts[1]).toByte())
        parts.drop(2).forEach { part ->
            var remaining = part
            val encoded = mutableListOf((remaining and 0x7f).toByte())
            remaining = remaining ushr 7
            while (remaining > 0) { encoded.add(0, ((remaining and 0x7f) or 0x80).toByte()); remaining = remaining ushr 7 }
            bytes += encoded
        }
        return der(0x06, bytes.toByteArray())
    }
    private fun der(tag: Int, content: ByteArray): ByteArray {
        val length = when {
            content.size < 128 -> byteArrayOf(content.size.toByte())
            content.size <= 0xff -> byteArrayOf(0x81.toByte(), content.size.toByte())
            content.size <= 0xffff -> byteArrayOf(0x82.toByte(), (content.size ushr 8).toByte(), content.size.toByte())
            else -> error("DER value exceeds bounded certificate size")
        }
        return byteArrayOf(tag.toByte()) + length + content
    }

    private val IPV4 = Regex("(?:[0-9]{1,3}\\.){3}[0-9]{1,3}")
    private const val DAY_MILLIS = 24L * 60 * 60 * 1000
}
