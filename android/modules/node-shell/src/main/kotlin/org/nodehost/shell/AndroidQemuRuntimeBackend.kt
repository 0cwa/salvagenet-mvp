package org.nodehost.shell

import android.content.Context
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.security.MessageDigest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.nodehost.core.OperationContext
import org.nodehost.core.RuntimeBackend
import org.nodehost.core.RuntimeStep
import org.nodehost.core.StepOutcome
import org.nodehost.model.ArtifactRef
import org.nodehost.model.BootSpec
import org.nodehost.model.DataDiskSpec
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.DiskFormat
import org.nodehost.model.HealthKind
import org.nodehost.model.HealthSpec
import org.nodehost.model.InitializationKind
import org.nodehost.model.InitializationSpec
import org.nodehost.model.MachineSpec
import org.nodehost.model.ProfileRequirements
import org.nodehost.model.RecoverySshSpec
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.SystemDiskSpec
import org.nodehost.model.VmProfile
import org.nodehost.model.VmProfileId
import org.nodehost.model.WritableLayer
import org.nodehost.qemu.BootstrapToken
import org.nodehost.qemu.QemuLaunchPlan
import org.nodehost.qemu.QemuProcessHandle
import org.nodehost.qemu.QemuProfileResolver
import org.nodehost.qemu.QemuRuntimeAdapter
import org.nodehost.qemu.QemuRuntimeAllocation
import org.nodehost.qemu.RecoverySshHostPort

/** RuntimeBackend adapter whose only process effect is the typed runtime-qemu API. */
class AndroidQemuRuntimeBackend(
    context: Context,
    private val desiredRuntime: suspend () -> RuntimeSpec?,
    private val bootstrapToken: suspend () -> String?,
    private val recoveryPort: RecoverySshHostPort = RecoverySshHostPort(19922),
    private val qemu: QemuRuntimeAdapter = QemuRuntimeAdapter(),
) : RuntimeBackend {
    private val application = context.applicationContext
    private val artifactRoot = File(application.filesDir, "nodehost-artifacts")
    private val resolver = QemuProfileResolver()
    private val stateLock = Any()
    private var handle: QemuProcessHandle? = null
    private var launchPlan: QemuLaunchPlan? = null
    private var profileId: VmProfileId? = null
    private var qmpReady = false
    private var guestReady = false
    private var stopping = false

    override suspend fun observe(id: RuntimeId): RuntimeObservation = synchronized(stateLock) {
        require(id == RuntimeId.DEFAULT) { "MVP supports one runtime" }
        when {
            handle != null && stopping -> RuntimeObservation.Stopping(id, handle?.processId, false)
            handle != null && qmpReady -> RuntimeObservation.Running(id, handle?.processId, guestReady)
            handle != null -> RuntimeObservation.Starting(id, handle?.processId)
            instanceDirectory().isDirectory -> RuntimeObservation.Stopped(id, profileId)
            else -> RuntimeObservation.Absent(id)
        }
    }

    override suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome {
        val desired = desiredRuntime() ?: error("desired runtime disappeared")
        require(desired.id == RuntimeId.DEFAULT) { "MVP supports one runtime" }
        return when (step) {
            RuntimeStep.VerifyProfile -> {
                require(desired.desiredState == DesiredRuntimeState.RUNNING)
                profile(desired.profileId, verifyArtifacts = true)
                StepOutcome(false, "profile=${desired.profileId.value}")
            }
            RuntimeStep.ResolveArtifacts -> {
                profile(desired.profileId, verifyArtifacts = true)
                StepOutcome(false, "artifacts-verified")
            }
            RuntimeStep.PrepareDisks -> withContext(Dispatchers.IO) {
                prepareDisks(desired)
                StepOutcome(true, "disks-prepared")
            }
            RuntimeStep.PrepareBoot -> {
                val token = bootstrapToken()?.let(::BootstrapToken)
                val allocation = QemuRuntimeAllocation.fromApplication(application, recoveryPort, token)
                val resolved = resolver.resolve(profile(desired.profileId, verifyArtifacts = true), desired, allocation)
                synchronized(stateLock) { launchPlan = resolved; profileId = desired.profileId }
                StepOutcome(true, "boot-prepared")
            }
            RuntimeStep.StartProcess -> {
                val plan = synchronized(stateLock) { checkNotNull(launchPlan) { "boot is not prepared" } }
                val started = qemu.start(plan)
                synchronized(stateLock) { handle = started; qmpReady = false; guestReady = false; stopping = false }
                StepOutcome(true, "qemu-started")
            }
            RuntimeStep.WaitForQmp -> {
                awaitFile(File(instanceDirectory(), "qmp.sock"), QMP_WAIT_MILLIS)
                synchronized(stateLock) { checkNotNull(handle); qmpReady = true }
                StepOutcome(false, "qmp-ready")
            }
            RuntimeStep.WaitForGuest -> {
                // The bootstrap callback creates this app-private marker after capability verification.
                awaitFile(File(instanceDirectory(), "guest-ready"), GUEST_WAIT_MILLIS)
                synchronized(stateLock) { checkNotNull(handle); guestReady = true }
                StepOutcome(false, "guest-ready")
            }
            RuntimeStep.RequestShutdown -> {
                val active = synchronized(stateLock) { stopping = true; handle }
                if (active != null) qemu.requestGuestShutdown(active)
                StepOutcome(active != null, "shutdown-requested")
            }
            RuntimeStep.ForceStop -> {
                qemu.forceStop()
                synchronized(stateLock) { handle = null; qmpReady = false; guestReady = false; stopping = false }
                StepOutcome(true, "qemu-force-stopped")
            }
            RuntimeStep.RemoveSystem -> withContext(Dispatchers.IO) {
                check(synchronized(stateLock) { handle == null }) { "cannot remove a running runtime" }
                val instance = instanceDirectory()
                val data = File(instance, "data.raw")
                if (desired.preserveDataOnDelete && data.exists()) data.renameTo(File(application.filesDir, "preserved-data.raw"))
                deleteBounded(instance, MAX_DELETE_ENTRIES)
                StepOutcome(true, "system-removed")
            }
        }
    }

    private fun profile(id: VmProfileId, verifyArtifacts: Boolean): VmProfile {
        require(id.value == UBUNTU_PROFILE) { "unsupported profile: ${id.value}" }
        val cloud = artifact("ubuntu-2404-arm64-cloud", verifyArtifacts)
        val code = artifact("aavmf-code", verifyArtifacts)
        val vars = artifact("aavmf-vars", verifyArtifacts)
        return VmProfile(
            id = id,
            version = 1,
            machine = MachineSpec(cpuModel = "max"),
            boot = BootSpec.Uefi(code, vars),
            systemDisk = SystemDiskSpec(cloud, DiskFormat.QCOW2, WritableLayer.QCOW2_OVERLAY),
            dataDisk = DataDiskSpec(8, true),
            initialization = InitializationSpec(InitializationKind.NOCLOUD_NET, "guest-init/ubuntu/vendor-data.yaml", "/v1/bootstrap/{token}/"),
            recoverySsh = RecoverySshSpec(),
            health = HealthSpec(HealthKind.METADATA_CALLBACK),
            requirements = ProfileRequirements(768, 5, setOf("uefi", "cloud-init", "openssh")),
        )
    }

    private fun artifact(id: String, verify: Boolean): ArtifactRef {
        val file = File(artifactRoot, id)
        require(file.isFile && file.length() in 1..MAX_ARTIFACT_BYTES) { "trusted artifact is missing or out of bounds: $id" }
        val digest = sha256(file)
        if (verify) {
            val expected = File(artifactRoot, "$id.sha256")
            require(expected.isFile && expected.length() <= 128) { "artifact digest metadata is missing: $id" }
            require(expected.readText().trim() == digest) { "artifact digest mismatch: $id" }
        }
        return ArtifactRef(id, digest, file.length())
    }

    private fun prepareDisks(runtime: RuntimeSpec) {
        val instance = instanceDirectory().apply { check(mkdirs() || isDirectory) }
        val artifacts = File(instance, "artifacts").apply { check(mkdirs() || isDirectory) }
        copyVerified("aavmf-code", File(artifacts, "AAVMF_CODE.fd"))
        copyVerified("aavmf-vars", File(instance, "firmware-vars.fd"))
        copyVerified("ubuntu-2404-arm64-cloud", File(instance, "system.qcow2"))
        val data = File(instance, "data.raw")
        if (!data.exists()) RandomAccessFile(data, "rw").use { it.setLength(runtime.dataDiskGiB * GIB) }
    }

    private fun copyVerified(id: String, target: File) {
        val source = File(artifactRoot, id)
        artifact(id, true)
        if (target.isFile && target.length() == source.length() && sha256(target) == sha256(source)) return
        val temporary = File(target.parentFile, target.name + ".tmp")
        FileInputStream(source).use { input -> FileOutputStream(temporary).use { output -> input.copyTo(output, COPY_BUFFER_BYTES); output.fd.sync() } }
        check(temporary.renameTo(target)) { "atomic artifact publication failed: $id" }
    }

    private suspend fun awaitFile(file: File, timeoutMillis: Long) {
        val end = android.os.SystemClock.elapsedRealtime() + timeoutMillis
        while (!file.exists()) {
            check(android.os.SystemClock.elapsedRealtime() < end) { "runtime readiness deadline exceeded: ${file.name}" }
            delay(POLL_MILLIS)
        }
    }

    private fun instanceDirectory() = File(application.filesDir, "vms/default")

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(COPY_BUFFER_BYTES)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun deleteBounded(root: File, remaining: Int): Int {
        if (!root.exists()) return remaining
        require(remaining > 0) { "runtime deletion exceeded entry bound" }
        var budget = remaining - 1
        root.listFiles()?.forEach { budget = deleteBounded(it, budget) }
        check(root.delete()) { "failed to delete runtime path" }
        return budget
    }

    private companion object {
        const val UBUNTU_PROFILE = "ubuntu-2404-arm64-uefi"
        const val COPY_BUFFER_BYTES = 1024 * 1024
        const val MAX_ARTIFACT_BYTES = 64L * 1024 * 1024 * 1024
        const val MAX_DELETE_ENTRIES = 4096
        const val QMP_WAIT_MILLIS = 10_000L
        const val GUEST_WAIT_MILLIS = 25_000L
        const val POLL_MILLIS = 100L
        const val GIB = 1024L * 1024 * 1024
    }
}
