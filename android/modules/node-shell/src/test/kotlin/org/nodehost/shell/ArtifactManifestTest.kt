package org.nodehost.shell

import java.io.File
import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class ArtifactManifestTest {
    @get:Rule val temporary = TemporaryFolder()

    @Test fun strictManifestRoundTripsAndListsActiveArtifact() {
        val root = temporary.newFolder("artifacts")
        val store = ArtifactManifestStore(root)
        val bytes = "artifact-payload".toByteArray()
        val digest = sha256(bytes)
        val payload = store.versionPayload("ubuntu-image", digest)
        payload.parentFile!!.mkdirs()
        payload.writeBytes(bytes)

        store.writeActive(ArtifactManifest("ubuntu-image", digest, bytes.size.toLong()), "test")

        val manifest = store.active("ubuntu-image")!!
        assertEquals(digest, manifest.sha256)
        assertEquals(bytes.size.toLong(), manifest.sizeBytes)
        assertEquals(payload.canonicalFile, store.payload(manifest))
        assertEquals(listOf(manifest), store.listActive())
        assertTrue(store.isPublished("ubuntu-image", digest, bytes.size.toLong(), verifyDigest = true))
    }

    @Test fun malformedOrEscapingManifestFailsClosed() {
        val root = temporary.newFolder("artifacts")
        val digest = "a".repeat(64)
        File(root, "bad.manifest.json").writeText(
            """{"version":1,"sha256":"$digest","sizeBytes":1,"relativePath":"../escape","extra":true}"""
        )

        assertThrows(IllegalStateException::class.java) { ArtifactManifestStore(root).active("bad") }
    }

    @Test fun digestVerificationDistinguishesFastPublicationCheck() {
        val root = temporary.newFolder("artifacts")
        val store = ArtifactManifestStore(root)
        val expected = "expected".toByteArray()
        val digest = sha256(expected)
        val payload = store.versionPayload("image", digest)
        payload.parentFile!!.mkdirs()
        payload.writeBytes("tampered".toByteArray())
        store.writeActive(ArtifactManifest("image", digest, payload.length()), "test")

        assertTrue(store.isPublished("image", digest, payload.length(), verifyDigest = false))
        assertFalse(store.isPublished("image", digest, payload.length(), verifyDigest = true))
    }

    private fun sha256(bytes: ByteArray) = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }
}
