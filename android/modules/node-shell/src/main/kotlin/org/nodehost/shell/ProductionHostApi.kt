package org.nodehost.shell

import android.content.Context
import android.os.SystemClock
import androidx.room.withTransaction
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.URI
import java.net.URL
import java.security.MessageDigest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.nodehost.api.HostCapability
import org.nodehost.api.HostDiagnostics
import org.nodehost.api.HostImage
import org.nodehost.api.HostMutationUseCases
import org.nodehost.api.HostProfile
import org.nodehost.api.HostResourceQueries
import org.nodehost.api.HostStatus
import org.nodehost.api.HostVm
import org.nodehost.api.ImageImportRequest
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.HostMesh
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.OperationId
import org.nodehost.model.OperationRecord
import org.nodehost.model.OperationState
import org.nodehost.model.RuntimeId
import org.nodehost.store.NodeHostDatabase
import org.nodehost.store.OperationEntity
import org.nodehost.store.RoomOperationRepository

private val OperationRecord.blocksArtifactEffects: Boolean
    get() = state.terminal || state == OperationState.CANCELLING

@JvmInline
value class TailnetBindAddress(val value: String) {
    init {
        org.nodehost.api.HostControlServer.requireSafeBindAddress(value)
        require(!InetAddress.getByName(value).isLoopbackAddress) { "API requires an actual tailnet address" }
    }
}

class AndroidHostResourceQueries(
    context: Context,
    private val database: NodeHostDatabase,
    private val operationsRepository: RoomOperationRepository,
    private val mesh: HostMesh,
    private val clockMillis: () -> Long,
) : HostResourceQueries {
    private val artifacts = File(context.filesDir, "nodehost-artifacts")
    private val deviceId = android.provider.Settings.Secure.getString(
        context.contentResolver, android.provider.Settings.Secure.ANDROID_ID,
    )?.take(128).orEmpty().ifEmpty { "android-node" }

    override suspend fun status(): HostStatus {
        val meshState = mesh.status().state.name.lowercase()
        val runtime = operationsRepository.current(RuntimeId.DEFAULT)?.javaClass?.simpleName?.lowercase() ?: "unknown"
        return HostStatus(deviceId, meshState, runtime)
    }
    override suspend fun capabilities() = listOf(
        HostCapability("vm.single", true), HostCapability("image.https-import", true),
        HostCapability("recovery.ssh", true),
    )
    override suspend fun profiles() = listOf(HostProfile("ubuntu-2404-arm64-uefi", 1, "UEFI"))
    override suspend fun images(): List<HostImage> = withContext(Dispatchers.IO) {
        val files = artifacts.listFiles()?.filter { it.isFile && !it.name.endsWith(".sha256") && IMAGE_ID.matches(it.name) }
            ?.sortedBy { it.name }?.take(128).orEmpty()
        files.mapNotNull { file ->
            val digest = File(artifacts, "${file.name}.sha256").takeIf(File::isFile)?.readText()?.trim()
            digest?.takeIf { SHA256.matches(it) }?.let { HostImage(file.name, it, file.length()) }
        }
    }
    override suspend fun vms(): List<HostVm> = vm(RuntimeId.DEFAULT)?.let(::listOf).orEmpty()
    override suspend fun vm(id: RuntimeId): HostVm? {
        require(id == RuntimeId.DEFAULT) { "MVP supports one runtime" }
        return operationsRepository.loadDesiredRuntime(id)?.let {
            HostVm(it.id.value, it.generation, it.desiredState.name.lowercase(), it.profileId.value, it.memoryMiB, it.vcpus, it.dataDiskGiB)
        }
    }
    override suspend fun operations(): List<OperationRecord> = withContext(Dispatchers.IO) {
        database.openHelper.readableDatabase.query(
            "SELECT id,idempotencyKey,requestDigest,runtimeId,desiredGeneration,state,currentStepId,errorCode FROM operations ORDER BY updatedAtEpochMillis DESC LIMIT 256",
        ).use { cursor -> buildList { while (cursor.moveToNext()) add(cursor.operation()) } }
    }
    override suspend fun operation(id: String): OperationRecord? = operationsRepository.load(OperationId(id))
    override suspend fun diagnostics() = HostDiagnostics(clockMillis(), mapOf(
        "api.transport" to "tls-tailnet", "runtime.limit" to "one", "artifact.count" to images().size.toString(),
    ))

    private fun android.database.Cursor.operation() = OperationRecord(
        OperationId(getString(0)), getString(1), getString(2), getString(3)?.let(::RuntimeId),
        if (isNull(4)) null else getLong(4), OperationState.valueOf(getString(5)), getString(6), getString(7),
    )
    private companion object {
        val IMAGE_ID = Regex("[a-z0-9][a-z0-9.-]{0,127}")
        val SHA256 = Regex("[a-f0-9]{64}")
    }
}

class AndroidHostMutations(
    context: Context,
    private val database: NodeHostDatabase,
    private val operations: RoomOperationRepository,
    private val applyRuntime: ApplyRuntimeUseCase,
    private val enrolledRepositoryOrigin: suspend () -> URI,
    private val operationIds: SecureOperationIdFactory = SecureOperationIdFactory(),
    private val clockMillis: () -> Long = System::currentTimeMillis,
) : HostMutationUseCases {
    private val artifacts = File(context.filesDir, "nodehost-artifacts")
    private val lock = Mutex()

    override suspend fun importImage(request: ImageImportRequest, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord {
        val digest = sha256(canonicalRequest)
        val (operation, newlyAccepted) = lock.withLock {
            existing(idempotencyKey)?.let {
                require(it.requestDigest == digest) { "idempotency key reused with different request" }
                return@withLock it to false
            }
            val accepted = OperationRecord(operationIds.newId(), idempotencyKey, digest, null, null, OperationState.ACCEPTED, null)
            insert(accepted)
            val preflight = update(accepted, accepted.transitionTo(OperationState.PREFLIGHT, "image.preflight"))
            update(preflight, preflight.transitionTo(OperationState.FETCHING, "image.fetch")) to true
        }
        if (!newlyAccepted) return operation
        try {
            val imageId = imageId(URI(request.sourceUrl))
            downloadVerified(request, enrolledRepositoryOrigin(), imageId, operation.id)
            return lock.withLock {
                val latest = requireNotNull(operations.load(operation.id))
                if (latest.blocksArtifactEffects) latest
                else {
                    val verified = update(latest, latest.transitionTo(OperationState.VERIFYING, "image.verify"))
                    val preparing = update(verified, verified.transitionTo(OperationState.PREPARING_DISKS, "image.publish"))
                    val prepared = update(preparing, preparing.transitionTo(OperationState.PREPARING_BOOT, "image.publish"))
                    update(prepared, prepared.transitionTo(OperationState.SUCCEEDED, null))
                }
            }
        } catch (failure: Throwable) {
            lock.withLock {
                val latest = requireNotNull(operations.load(operation.id))
                if (!latest.blocksArtifactEffects) {
                    update(latest, latest.transitionTo(OperationState.FAILED_RETRYABLE, "image.fetch", "IMAGE_IMPORT_FAILED"))
                }
            }
            throw failure
        }
    }

    override suspend fun removeVm(id: RuntimeId, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord {
        require(id == RuntimeId.DEFAULT) { "MVP supports one runtime" }
        val current = requireNotNull(operations.loadDesiredRuntime(id)) { "VM not found" }
        return applyRuntime.apply(current.copy(generation = current.generation + 1, desiredState = DesiredRuntimeState.ABSENT), idempotencyKey, canonicalRequest)
    }

    override suspend fun cancelOperation(id: String, idempotencyKey: String, canonicalRequest: ByteArray): OperationRecord = lock.withLock {
        operations.cancelOperation(
            OperationId(id),
            setOf(OperationState.ACCEPTED, OperationState.FETCHING, OperationState.FAILED_RETRYABLE),
        )
    }

    override suspend fun revokeController(id: String, idempotencyKey: String, canonicalRequest: ByteArray) {
        // The MVP enrollment carries one controller. Revocation is fail-closed and durable.
        ControllerRevocations.revoke(database.openHelper.writableDatabase, id, idempotencyKey, sha256(canonicalRequest), clockMillis())
    }

    private suspend fun downloadVerified(request: ImageImportRequest, authority: URI, imageId: String, operationId: OperationId) = withContext(Dispatchers.IO) {
        check(artifacts.mkdirs() || artifacts.isDirectory) { "artifact directory unavailable" }
        val destination = File(artifacts, imageId)
        val installedDigest = File(artifacts, "$imageId.sha256")
        if (destination.isFile && destination.length() == request.expectedSizeBytes &&
            installedDigest.isFile && installedDigest.readText().trim() == request.sha256
        ) return@withContext
        val temporary = File(artifacts, ".$imageId.${System.nanoTime()}.part")
        val deadline = SystemClock.elapsedRealtime() + DOWNLOAD_DEADLINE_MILLIS
        var current = URI(request.sourceUrl)
        try {
            FileOutputStream(temporary).use { output ->
                val digest = MessageDigest.getInstance("SHA-256")
                var redirects = 0
                while (true) {
                    validateArtifactUri(current, authority)
                    validatePublicAddresses(current.host)
                    val remaining = deadline - SystemClock.elapsedRealtime()
                    check(remaining > 0) { "image download deadline exceeded" }
                    val connection = URL(current.toString()).openConnection() as HttpURLConnection
                    connection.instanceFollowRedirects = false
                    connection.connectTimeout = minOf(10_000L, remaining).toInt()
                    connection.readTimeout = minOf(15_000L, remaining).toInt()
                    connection.requestMethod = "GET"
                    connection.connect()
                    try {
                        if (connection.responseCode in 300..399) {
                            require(++redirects <= MAX_REDIRECTS) { "too many image redirects" }
                            current = current.resolve(requireNotNull(connection.getHeaderField("Location")) { "redirect missing location" })
                            continue
                        }
                        require(connection.responseCode == 200) { "image server returned ${connection.responseCode}" }
                        val declared = connection.contentLengthLong
                        require(declared == -1L || declared == request.expectedSizeBytes) { "image size header mismatch" }
                        connection.inputStream.use { input ->
                            val buffer = ByteArray(BUFFER_BYTES)
                            var total = 0L
                            while (true) {
                                check(!operationCancelled(operationId)) { "image import cancelled" }
                                check(SystemClock.elapsedRealtime() < deadline) { "image download deadline exceeded" }
                                val count = input.read(buffer)
                                if (count < 0) break
                                total += count
                                require(total <= request.expectedSizeBytes) { "image exceeds expected size" }
                                output.write(buffer, 0, count)
                                digest.update(buffer, 0, count)
                            }
                            require(total == request.expectedSizeBytes) { "image size mismatch" }
                        }
                        require(digest.digest().joinToString("") { "%02x".format(it) } == request.sha256) { "image digest mismatch" }
                        output.flush(); output.fd.sync()
                        break
                    } finally { connection.disconnect() }
                }
            }
            java.nio.file.Files.move(
                temporary.toPath(), destination.toPath(),
                java.nio.file.StandardCopyOption.ATOMIC_MOVE, java.nio.file.StandardCopyOption.REPLACE_EXISTING,
            )
            val digestTemporary = File(artifacts, ".$imageId.sha256.part")
            FileOutputStream(digestTemporary).use { it.write((request.sha256 + "\n").toByteArray()); it.fd.sync() }
            java.nio.file.Files.move(
                digestTemporary.toPath(), File(artifacts, "$imageId.sha256").toPath(),
                java.nio.file.StandardCopyOption.ATOMIC_MOVE, java.nio.file.StandardCopyOption.REPLACE_EXISTING,
            )
        } finally { temporary.delete() }
    }

    private fun operationCancelled(id: OperationId): Boolean =
        database.openHelper.readableDatabase.query("SELECT state FROM operations WHERE id = ?", arrayOf(id.value)).use {
            it.moveToFirst() && OperationState.valueOf(it.getString(0)).let { state -> state.terminal || state == OperationState.CANCELLING }
        }

    private fun validateArtifactUri(uri: URI, authority: URI) {
        require(uri.scheme == "https" && uri.userInfo == null && uri.fragment == null && uri.host != null) { "invalid artifact URL" }
        require(uri.host.equals(authority.host, true) && effectivePort(uri) == effectivePort(authority)) {
            "artifact URL is outside enrolled repository origin"
        }
        val enrolledPath = authority.path.orEmpty().trimEnd('/')
        require(enrolledPath.isEmpty() || uri.path == enrolledPath || uri.path.startsWith("$enrolledPath/")) {
            "artifact URL is outside enrolled repository path"
        }
    }
    private fun validatePublicAddresses(host: String) {
        val addresses = InetAddress.getAllByName(host)
        require(addresses.isNotEmpty() && addresses.size <= 16) { "artifact host address count is out of bounds" }
        require(addresses.all { !it.isAnyLocalAddress && !it.isLoopbackAddress && !it.isLinkLocalAddress && !it.isSiteLocalAddress && !it.isMulticastAddress }) {
            "artifact host resolved to a non-public address"
        }
    }
    private fun imageId(uri: URI): String = uri.path.substringAfterLast('/').also {
        require(Regex("[a-z0-9][a-z0-9.-]{0,127}").matches(it)) { "artifact URL must end in a typed image id" }
    }
    private fun effectivePort(uri: URI) = if (uri.port >= 0) uri.port else 443
    private suspend fun existing(key: String) = database.dao().operationByKey(key)?.toRecord()
    private suspend fun insert(record: OperationRecord) = database.withTransaction {
        require(database.dao().operationCount() < RoomOperationRepository.MAX_RETAINED_OPERATIONS) { "operation journal capacity exceeded" }
        database.dao().insertOperation(record.toEntity(clockMillis()))
    }
    private suspend fun update(expected: OperationRecord, updated: OperationRecord): OperationRecord {
        check(operations.compareAndSetOperation(expected, updated)) { "operation changed concurrently" }
        return updated
    }
    private fun OperationRecord.toEntity(created: Long) = OperationEntity(id.value, idempotencyKey, requestDigest, runtimeId?.value, desiredGeneration, state.name, currentStepId, errorCode, created, clockMillis())
    private fun OperationEntity.toRecord() = OperationRecord(OperationId(id), idempotencyKey, requestDigest, runtimeId?.let(::RuntimeId), desiredGeneration, OperationState.valueOf(state), currentStepId, errorCode)
    private fun sha256(value: ByteArray) = MessageDigest.getInstance("SHA-256").digest(value).joinToString("") { "%02x".format(it) }

    private companion object {
        const val BUFFER_BYTES = 64 * 1024
        const val DOWNLOAD_DEADLINE_MILLIS = 15 * 60 * 1000L
        const val MAX_REDIRECTS = 5
    }
}

internal object ControllerRevocations {
    fun revoke(db: androidx.sqlite.db.SupportSQLiteDatabase, controllerId: String, key: String, digest: String, now: Long) {
        db.execSQL("CREATE TABLE IF NOT EXISTS controller_revocations (controllerId TEXT PRIMARY KEY NOT NULL, idempotencyKey TEXT NOT NULL UNIQUE, requestDigest TEXT NOT NULL, revokedAtEpochMillis INTEGER NOT NULL)")
        db.query("SELECT requestDigest FROM controller_revocations WHERE idempotencyKey = ?", arrayOf(key)).use {
            if (it.moveToFirst()) { require(it.getString(0) == digest) { "idempotency key reused with different request" }; return }
        }
        db.execSQL("INSERT INTO controller_revocations VALUES (?,?,?,?)", arrayOf<Any?>(controllerId, key, digest, now))
    }
    fun isRevoked(db: androidx.sqlite.db.SupportSQLiteDatabase, controllerId: String): Boolean {
        db.execSQL("CREATE TABLE IF NOT EXISTS controller_revocations (controllerId TEXT PRIMARY KEY NOT NULL, idempotencyKey TEXT NOT NULL UNIQUE, requestDigest TEXT NOT NULL, revokedAtEpochMillis INTEGER NOT NULL)")
        return db.query("SELECT 1 FROM controller_revocations WHERE controllerId = ? LIMIT 1", arrayOf(controllerId)).use { it.moveToFirst() }
    }
}
