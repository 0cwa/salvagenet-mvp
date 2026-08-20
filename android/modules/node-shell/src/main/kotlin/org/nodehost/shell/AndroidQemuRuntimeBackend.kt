package org.nodehost.shell

import android.content.Context
import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import org.nodehost.core.OperationContext
import org.nodehost.core.RuntimeBackend
import org.nodehost.core.RuntimeStep
import org.nodehost.core.StepOutcome
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfile
import org.nodehost.model.VmProfileId
import org.nodehost.qemu.BootstrapToken
import org.nodehost.qemu.QemuExit
import org.nodehost.qemu.QemuLaunchPlan
import org.nodehost.qemu.QemuProfileResolver
import org.nodehost.qemu.QemuRuntimeAdapter
import org.nodehost.qemu.QemuRuntimeAllocation
import org.nodehost.qemu.RecoverySshHostPort

internal data class ManagedQemuProcess(
    val processId: Long?,
    val awaitExit: suspend () -> QemuExit,
    val awaitQmpReady: suspend () -> String,
    val requestGuestShutdown: suspend () -> Unit,
)

internal interface QemuProcessControl {
    suspend fun start(plan: QemuLaunchPlan, runtime: RuntimeSpec): ManagedQemuProcess
    fun forceStop()
}

private class RuntimeQemuProcessControl(private val adapter: QemuRuntimeAdapter = QemuRuntimeAdapter()) : QemuProcessControl {
    override suspend fun start(plan: QemuLaunchPlan, runtime: RuntimeSpec): ManagedQemuProcess {
        val handle = adapter.start(plan)
        return ManagedQemuProcess(
            handle.processId,
            { adapter.awaitExit(handle) },
            { adapter.awaitQmpReady(handle) },
            { adapter.requestGuestShutdown(handle) },
        )
    }
    override fun forceStop() = adapter.forceStop()
}

/** RuntimeBackend adapter whose only process effect is the typed runtime-qemu API. */
internal class AndroidQemuRuntimeBackend(
    context: Context,
    private val desiredRuntime: suspend () -> RuntimeSpec?,
    private val beginBootToken: suspend (VmProfileId) -> String?,
    private val recoveryPort: RecoverySshHostPort,
    private val qemu: QemuProcessControl = RuntimeQemuProcessControl(),
    private val elapsedRealtimeMillis: () -> Long = android.os.SystemClock::elapsedRealtime,
    private val gracefulStopMillis: Long = GRACEFUL_STOP_MILLIS,
    private val forceExitMillis: Long = FORCE_EXIT_MILLIS,
    private val atomicMove: (File, File) -> Unit = { source, target ->
        Files.move(source.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE)
    },
) : RuntimeBackend {
    private val application = context.applicationContext
    private val storage = AndroidQemuProfileStorage(application, atomicMove)
    private val resolver = QemuProfileResolver()
    private val stateLock = Any()
    private var handle: ManagedQemuProcess? = null
    private var preparedLaunch: Pair<QemuLaunchPlan, RuntimeSpec>? = null
    private var profileId: VmProfileId? = null
    private var appliedGeneration: Long? = null
    private var qmpReady = false
    private var guestReady = false
    private var stopping = false
    private var gracefulDeadlineElapsedRealtime: Long? = null
    private var exitWatcher: Job? = null
    private var serviceScope: CoroutineScope? = null
    private var wakeReconciler: (() -> Unit)? = null

    /** Service-owned observation is attached after composition so process exit always wakes convergence. */
    fun attachLifecycle(scope: CoroutineScope, wake: () -> Unit) = synchronized(stateLock) {
        serviceScope = scope
        wakeReconciler = wake
        handle?.let(::watchExitLocked)
    }

    override suspend fun observe(id: RuntimeId): RuntimeObservation = synchronized(stateLock) {
        require(id == RuntimeId.DEFAULT) { "MVP supports one runtime" }
        when {
            handle != null && stopping -> RuntimeObservation.Stopping(
                id, handle?.processId,
                gracefulDeadlineElapsedRealtime?.let { elapsedRealtimeMillis() >= it } == true,
            )
            handle != null && qmpReady -> RuntimeObservation.Running(
                id, handle?.processId, guestReady,
                checkNotNull(appliedGeneration) { "running QEMU process has no applied generation" },
            )
            handle != null -> RuntimeObservation.Starting(id, handle?.processId)
            storage.instanceDirectory().isDirectory -> RuntimeObservation.Stopped(id, profileId)
            else -> RuntimeObservation.Absent(id)
        }
    }

    override suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome {
        val desired = desiredRuntime() ?: error("desired runtime disappeared")
        require(desired.id == RuntimeId.DEFAULT) { "MVP supports one runtime" }
        return when (step) {
            RuntimeStep.VerifyProfile -> {
                require(desired.desiredState == DesiredRuntimeState.RUNNING)
                storage.profile(desired.profileId, verifyArtifacts = true)
                StepOutcome(false, "profile=${desired.profileId.value}")
            }
            RuntimeStep.ResolveArtifacts -> {
                storage.profile(desired.profileId, verifyArtifacts = true)
                StepOutcome(false, "artifacts-verified")
            }
            RuntimeStep.PrepareDisks -> withContext(Dispatchers.IO) {
                storage.prepareDisks(desired)
                StepOutcome(true, "disks-prepared")
            }
            RuntimeStep.PrepareBoot -> {
                File(storage.instanceDirectory(), "guest-ready").delete()
                val token = beginBootToken(desired.profileId)?.let(::BootstrapToken)
                val allocation = QemuRuntimeAllocation.fromApplication(application, recoveryPort, token)
                val resolved = resolver.resolve(storage.profile(desired.profileId, verifyArtifacts = true), desired, allocation)
                synchronized(stateLock) { preparedLaunch = resolved to desired; profileId = desired.profileId }
                StepOutcome(true, "boot-prepared")
            }
            RuntimeStep.StartProcess -> {
                val prepared = synchronized(stateLock) { checkNotNull(preparedLaunch) { "boot is not prepared" } }
                val started = qemu.start(prepared.first, prepared.second)
                synchronized(stateLock) {
                    handle = started
                    appliedGeneration = prepared.second.generation
                    qmpReady = false
                    guestReady = false
                    stopping = false
                    gracefulDeadlineElapsedRealtime = null
                    watchExitLocked(started)
                }
                StepOutcome(true, "qemu-started")
            }
            RuntimeStep.WaitForQmp -> {
                awaitFile(File(storage.instanceDirectory(), "qmp.sock"), QMP_WAIT_MILLIS)
                val active = synchronized(stateLock) { checkNotNull(handle) }
                val qmpStatus = active.awaitQmpReady()
                require(qmpStatus in QMP_READY_STATUSES) { "QMP is responsive but not running: $qmpStatus" }
                synchronized(stateLock) {
                    check(handle === active) { "QEMU process changed during QMP readiness" }
                    qmpReady = true
                    // Legacy Alpine has no metadata callback; a real running QMP monitor is its bounded readiness gate.
                    if (profileId?.value == ALPINE_PROFILE_ID) guestReady = true
                }
                StepOutcome(false, "qmp-ready:$qmpStatus")
            }
            RuntimeStep.WaitForGuest -> {
                val needsCallback = synchronized(stateLock) { profileId?.value != ALPINE_PROFILE_ID }
                if (needsCallback) awaitFile(File(storage.instanceDirectory(), "guest-ready"), GUEST_WAIT_MILLIS)
                synchronized(stateLock) { checkNotNull(handle); guestReady = true }
                StepOutcome(false, "guest-ready")
            }
            RuntimeStep.RequestShutdown -> {
                val active = synchronized(stateLock) {
                    stopping = true
                    gracefulDeadlineElapsedRealtime = elapsedRealtimeMillis() + gracefulStopMillis
                    handle
                }
                if (active != null) active.requestGuestShutdown()
                serviceScope?.launch {
                    delay(gracefulStopMillis)
                    synchronized(stateLock) { if (handle === active && stopping) wakeReconciler?.invoke() }
                }
                StepOutcome(active != null, "shutdown-requested")
            }
            RuntimeStep.ForceStop -> {
                val active = synchronized(stateLock) { handle }
                if (active != null) {
                    qemu.forceStop()
                    try {
                        withTimeout(forceExitMillis) { active.awaitExit() }
                    } finally {
                        if (synchronized(stateLock) { handle === active }) {
                            serviceScope?.launch { delay(POLL_MILLIS); wakeReconciler?.invoke() }
                        }
                    }
                }
                StepOutcome(active != null, "qemu-force-stopped")
            }
            RuntimeStep.RemoveSystem -> withContext(Dispatchers.IO) {
                check(synchronized(stateLock) { handle == null }) { "cannot remove a running runtime" }
                storage.removeSystem(desired)
                synchronized(stateLock) {
                    preparedLaunch = null
                    profileId = null
                    appliedGeneration = null
                }
                StepOutcome(true, "system-removed")
            }
        }
    }

    internal fun profile(id: VmProfileId, verifyArtifacts: Boolean): VmProfile =
        storage.profile(id, verifyArtifacts)

    private suspend fun awaitFile(file: File, timeoutMillis: Long) {
        val end = elapsedRealtimeMillis() + timeoutMillis
        while (!file.exists()) {
            check(synchronized(stateLock) { handle != null }) { "QEMU exited before runtime readiness: ${file.name}" }
            check(elapsedRealtimeMillis() < end) { "runtime readiness deadline exceeded: ${file.name}" }
            delay(POLL_MILLIS)
        }
    }

    private fun watchExitLocked(started: ManagedQemuProcess) {
        val scope = serviceScope ?: return
        exitWatcher?.cancel()
        exitWatcher = scope.launch {
            val result = runCatching { started.awaitExit() }
            result.onSuccess { android.util.Log.i(TAG, "QEMU exited code=${it.code}") }
                .onFailure { android.util.Log.e(TAG, "QEMU exit observation failed class=${it::class.java.simpleName}") }
            synchronized(stateLock) {
                if (handle === started) {
                    handle = null
                    appliedGeneration = null
                    qmpReady = false
                    guestReady = false
                    stopping = false
                    gracefulDeadlineElapsedRealtime = null
                    wakeReconciler?.invoke()
                }
            }
        }
    }

    private companion object {
        const val TAG = "NodeHostQemu"
        val QMP_READY_STATUSES = setOf("running")
        const val QMP_WAIT_MILLIS = 10_000L
        const val GUEST_WAIT_MILLIS = 25_000L
        const val POLL_MILLIS = 100L
        const val GRACEFUL_STOP_MILLIS = 20_000L
        const val FORCE_EXIT_MILLIS = 5_000L
    }
}
