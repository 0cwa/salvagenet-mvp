package org.nodehost.shell

import androidx.test.core.app.ApplicationProvider
import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertThrows
import org.junit.Before
import org.junit.Test
import org.nodehost.api.ArtifactUploadCreateRequest
import org.nodehost.api.ArtifactUploadState
import org.nodehost.api.HostApiConflictException

class AndroidArtifactUploadsTest {
    private val context = ApplicationProvider.getApplicationContext<android.content.Context>()
    private var now = 1_000L
    private var idCounter = 0

    @Before fun cleanBefore(): Unit = clean()
    @After fun cleanAfter(): Unit = clean()

    @Test fun createIsIdempotentAndSurvivesAdapterRecreation(): Unit = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val store = store()
        val first = store.createUpload(request, "idempotency-key-001", "request-one".toByteArray())
        val replay = store.createUpload(request, "idempotency-key-001", "request-one".toByteArray())
        val restored = store().upload(first.id)
        assertEquals(first, replay)
        assertEquals(first, restored)
        assertThrows(HostApiConflictException::class.java) {
            runBlocking { store.createUpload(request, "idempotency-key-001", "different".toByteArray()) }
        }
    }

    @Test fun sequentialChunksReplayAndPublishAtomically(): Unit = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val store = store()
        val upload = store.createUpload(request, "idempotency-key-002", "request-two".toByteArray())
        val first = bytes.copyOfRange(0, 4)
        val second = bytes.copyOfRange(4, 8)
        assertEquals(4L, store.writeChunk(upload.id, 0, sha256(first), first).committedBytes)
        assertEquals(4L, store.writeChunk(upload.id, 0, sha256(first), first).committedBytes)
        assertThrows(HostApiConflictException::class.java) {
            runBlocking { store.writeChunk(upload.id, 5, sha256(second), second) }
        }
        val conflict = "zzzz".toByteArray()
        assertThrows(HostApiConflictException::class.java) {
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

    @Test fun recoveryTruncatesBytesNotCommittedInMetadata(): Unit = runBlocking {
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

    @Test fun recoveryFinishesStalePayloadMovedBeforeManifestPublication(): Unit = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val store = store()
        val upload = store.createUpload(request, "idempotency-key-004", "request-four".toByteArray())
        store.writeChunk(upload.id, 0, request.sha256, bytes)
        val staged = File(context.filesDir, "nodehost-uploads/${upload.id}/payload.part")
        val published = File(context.filesDir, "nodehost-artifacts/versions/ubuntu-test/${request.sha256}/payload")
        published.parentFile!!.mkdirs()
        Files.move(staged.toPath(), published.toPath(), StandardCopyOption.ATOMIC_MOVE)
        now += 2L * 24 * 60 * 60 * 1_000

        store().recoverAndCollect()
        val recovered = store().upload(upload.id)

        assertEquals(ArtifactUploadState.COMPLETED, recovered?.state)
        assertEquals(bytes.size.toLong(), recovered?.committedBytes)
        val manifest = JSONObject(File(context.filesDir, "nodehost-artifacts/ubuntu-test.manifest.json").readText())
        assertEquals(request.sha256, manifest.getString("sha256"))
    }

    @Test fun staleAndCancelledRecordsDoNotConsumeOpenUploadCapacity(): Unit = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val store = store()
        repeat(20) { index ->
            val upload = store.createUpload(
                request,
                "cancelled-key-${index.toString().padStart(4, '0')}",
                "cancelled-request-$index".toByteArray(),
            )
            store.cancelUpload(upload.id)
        }
        val fresh = store.createUpload(request, "idempotency-key-fresh", "fresh-request".toByteArray())
        assertEquals(ArtifactUploadState.OPEN, fresh.state)

        now += 2L * 24 * 60 * 60 * 1_000
        store.recoverAndCollect()
        assertEquals(ArtifactUploadState.CANCELLED, store.upload(fresh.id)?.state)
        val restarted = store.createUpload(request, "idempotency-key-fresh", "fresh-request".toByteArray())
        assertEquals(ArtifactUploadState.OPEN, restarted.state)
        assertNotEquals(fresh.id, restarted.id)
    }

    @Test fun persistedMetadataVersionFailsClosed(): Unit = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val request = ArtifactUploadCreateRequest("ubuntu-test", sha256(bytes), bytes.size.toLong())
        val upload = store().createUpload(request, "idempotency-key-005", "request-five".toByteArray())
        val metadataFile = File(context.filesDir, "nodehost-uploads/${upload.id}/metadata.json")
        val metadata = JSONObject(metadataFile.readText()).put("version", 2)
        metadataFile.writeText(metadata.toString())
        assertThrows(IllegalStateException::class.java) {
            runBlocking { store().upload(upload.id) }
        }
    }

    @Test fun activeManifestWithUnknownFieldsIsNotTrusted(): Unit = runBlocking {
        val bytes = "abcdefgh".toByteArray()
        val digest = sha256(bytes)
        val payload = File(context.filesDir, "nodehost-artifacts/versions/ubuntu-test/$digest/payload")
        payload.parentFile!!.mkdirs()
        payload.writeBytes(bytes)
        val manifest = File(context.filesDir, "nodehost-artifacts/ubuntu-test.manifest.json")
        manifest.parentFile!!.mkdirs()
        manifest.writeText(
            JSONObject()
                .put("version", 1)
                .put("sha256", digest)
                .put("sizeBytes", bytes.size)
                .put("relativePath", "versions/ubuntu-test/$digest/payload")
                .put("unknown", true)
                .toString()
        )
        val upload = store().createUpload(
            ArtifactUploadCreateRequest("ubuntu-test", digest, bytes.size.toLong()),
            "idempotency-key-006",
            "request-six".toByteArray(),
        )
        assertEquals(ArtifactUploadState.OPEN, upload.state)
    }

    @Test fun missingUploadIsNotFound() {
        assertThrows(NoSuchElementException::class.java) {
            runBlocking { store().completeUpload("upload-${"f".repeat(32)}") }
        }
    }

    private fun store() = AndroidArtifactUploadStore(
        context,
        { now },
        idFactory = {
            idCounter += 1
            "upload-${idCounter.toString(16).padStart(32, '0')}"
        },
    )

    private fun clean() {
        File(context.filesDir, "nodehost-uploads").deleteRecursively()
        File(context.filesDir, "nodehost-artifacts").deleteRecursively()
    }

    private fun sha256(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it) }
}
