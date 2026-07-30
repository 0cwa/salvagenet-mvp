package org.nodehost.shell

import androidx.test.core.app.ApplicationProvider
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Before
import org.junit.Test
import org.nodehost.api.ArtifactUploadCreateRequest
import org.nodehost.api.ArtifactUploadState

class AndroidArtifactUploadsTest {
    private val context = ApplicationProvider.getApplicationContext<android.content.Context>()
    private var now = 1_000L
    private var idCounter = 0

    @Before fun cleanBefore() = clean()
    @After fun cleanAfter() = clean()

    @Test fun createIsIdempotentAndSurvivesAdapterRecreation() = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val store = store()
        val first = store.createUpload(request, "idempotency-key-001", "request-one".toByteArray())
        val replay = store.createUpload(request, "idempotency-key-001", "request-one".toByteArray())
        val restored = store().upload(first.id)
        assertEquals(first, replay)
        assertEquals(first, restored)
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { store.createUpload(request, "idempotency-key-001", "different".toByteArray()) }
        }
    }

    @Test fun sequentialChunksReplayAndPublishAtomically() = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val store = store()
        val upload = store.createUpload(request, "idempotency-key-002", "request-two".toByteArray())
        val first = bytes.copyOfRange(0, 4)
        val second = bytes.copyOfRange(4, 8)
        assertEquals(4L, store.writeChunk(upload.id, 0, sha256(first), first).committedBytes)
        assertEquals(4L, store.writeChunk(upload.id, 0, sha256(first), first).committedBytes)
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { store.writeChunk(upload.id, 5, sha256(second), second) }
        }
        val conflict = "zzzz".toByteArray()
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { store.writeChunk(upload.id, 0, sha256(conflict), conflict) }
        }
        assertEquals(8L, store.writeChunk(upload.id, 4, sha256(second), second).committedBytes)
        val image = store.completeUpload(upload.id)
        assertEquals("ubuntu-test", image.id)
        assertEquals(image, store.completeUpload(upload.id))
        assertEquals(ArtifactUploadState.COMPLETED, store.cancelUpload(upload.id).state)
        val payload = File(context.filesDir, "nodehost-artifacts/versions/ubuntu-test/${request.sha256}/payload")
        val manifest = File(context.filesDir, "nodehost-artifacts/ubuntu-test.manifest.json")
        assertEquals(bytes.toList(), payload.readBytes().toList())
        assertEquals(true, manifest.isFile)
    }

    @Test fun recoveryTruncatesBytesNotCommittedInMetadata() = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val store = store()
        val upload = store.createUpload(request, "idempotency-key-003", "request-three".toByteArray())
        val first = bytes.copyOfRange(0, 4)
        store.writeChunk(upload.id, 0, sha256(first), first)
        val payload = File(context.filesDir, "nodehost-uploads/${upload.id}/payload.part")
        FileOutputStream(payload, true).use { it.write("orphan".toByteArray()) }
        assertEquals(4L, store().upload(upload.id)?.committedBytes)
        assertEquals(4L, payload.length())
    }

    @Test fun staleOpenUploadIsCancelledWithoutPublishing() = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val store = store()
        val upload = store.createUpload(request, "idempotency-key-004", "request-four".toByteArray())
        now += 2L * 24 * 60 * 60 * 1_000
        store.recoverAndCollect()
        assertEquals(ArtifactUploadState.CANCELLED, store.upload(upload.id)?.state)
        assertEquals(false, File(context.filesDir, "nodehost-artifacts/ubuntu-test.manifest.json").exists())
    }

    private fun store() = AndroidArtifactUploadStore(context, { now }) {
        idCounter += 1
        "upload-${idCounter.toString(16).padStart(32, '0')}"
    }

    private fun clean() {
        File(context.filesDir, "nodehost-uploads").deleteRecursively()
        File(context.filesDir, "nodehost-artifacts").deleteRecursively()
    }

    private fun sha256(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it) }
}
