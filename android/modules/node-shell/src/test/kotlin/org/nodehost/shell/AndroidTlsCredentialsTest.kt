package org.nodehost.shell

import java.net.InetAddress
import java.security.KeyPairGenerator
import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidTlsCredentialsTest {
    @Test fun generatedCertificateCarriesActualTailnetIpSan() {
        val keys = KeyPairGenerator.getInstance("EC").apply { initialize(256) }.generateKeyPair()
        val address = InetAddress.getByName("100.64.0.9")
        val certificate = AndroidTlsCredentials.addressCertificate(keys.private, keys.public, address, 1_700_000_000_000L)
        certificate.verify(keys.public)
        assertTrue(certificate.subjectAlternativeNames.any { it[0] == 7 && InetAddress.getByName(it[1].toString()) == address })
    }
}
