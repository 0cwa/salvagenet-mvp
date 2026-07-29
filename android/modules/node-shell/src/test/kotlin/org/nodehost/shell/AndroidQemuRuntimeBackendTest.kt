package org.nodehost.shell

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import java.io.File
import java.security.MessageDigest
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.nodehost.core.OperationContext
import org.nodehost.core.RuntimeStep
import org.nodehost.model.BootSpec
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.OperationId
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId
import org.nodehost.qemu.QemuExit
import org.nodehost.qemu.QemuLaunchPlan
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class AndroidQemuRuntimeBackendTest {
    private lateinit var context: Context
    private lateinit var scope: CoroutineScope

    @Before fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        context.applicationInfo.nativeLibraryDir = File(context.filesDir, "native-libs").apply { mkdirs() }.path
        File(context.filesDir, "nodehost-artifacts").deleteRecursively()
        File(context.filesDir, "vms").deleteRecursively()
        scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        installArtifacts()
    }

    @After fun tearDown() {
        scope.cancel()
        File(context.filesDir, "nodehost-artifacts").deleteRecursively()
        File(context.filesDir, "vms").deleteRecursively()
    }

    @Test fun allAdvertisedProfilesResolveToBackedTypedBootModes() {
        val backend = backend(FakeQemuControl())
        assertTrue(backend.profile(VmProfileId("alpine-direct-qualification"), true).boot is BootSpec.DirectKernel)
        assertTrue(backend.profile(VmProfileId("ubuntu-2404-arm64-uefi"), true).boot is BootSpec.Uefi)
        val k3s = backend.profile(VmProfileId("k3s-worker-lab"), true)
        assertTrue(k3s.boot is BootSpec.Uefi)
        assertEquals(VmProfileId("ubuntu-2404-arm64-uefi"), k3s.extends)
        assertTrue(k3s.requirements.qualificationChecks.contains("tailscale-reachability"))
    }

    @Test fun gracefulDeadlineForceStopExitAndWakeAreObserved() = runBlocking {
        var elapsed = 0L
        var wakes = 0
        val qemu = FakeQemuControl()
        val backend = backend(qemu, elapsedRealtime = { elapsed })
        backend.attachLifecycle(scope) { wakes++ }
        backend.execute(operationContext("prepare"), RuntimeStep.PrepareBoot)
        backend.execute(operationContext("start"), RuntimeStep.StartProcess)
        assertTrue(backend.observe(RuntimeId.DEFAULT) is RuntimeObservation.Starting)

        backend.execute(operationContext("shutdown"), RuntimeStep.RequestShutdown)
        assertEquals(1, qemu.shutdownRequests)
        assertFalse((backend.observe(RuntimeId.DEFAULT) as RuntimeObservation.Stopping).gracefulDeadlineExceeded)
        elapsed = 11
        assertTrue((backend.observe(RuntimeId.DEFAULT) as RuntimeObservation.Stopping).gracefulDeadlineExceeded)

        backend.execute(operationContext("force"), RuntimeStep.ForceStop)
        withTimeout(2_000) { while (wakes == 0) kotlinx.coroutines.yield() }
        assertEquals(1, qemu.forceStops)
        assertTrue(backend.observe(RuntimeId.DEFAULT) is RuntimeObservation.Absent)
    }

    @Test fun spontaneousProcessExitClearsRuntimeAndWakesReconciliation() = runBlocking {
        var wakes = 0
        val qemu = FakeQemuControl()
        val backend = backend(qemu)
        backend.attachLifecycle(scope) { wakes++ }
        backend.execute(operationContext("prepare"), RuntimeStep.PrepareBoot)
        backend.execute(operationContext("start"), RuntimeStep.StartProcess)

        qemu.exit.complete(QemuExit(17, listOf("bounded diagnostic")))
        withTimeout(2_000) { while (wakes == 0) kotlinx.coroutines.yield() }
        assertTrue(backend.observe(RuntimeId.DEFAULT) is RuntimeObservation.Absent)
    }

    private fun backend(
        qemu: FakeQemuControl,
        elapsedRealtime: () -> Long = { 0L },
    ) = AndroidQemuRuntimeBackend(
        context,
        desiredRuntime = { RuntimeSpec(generation = 1, desiredState = DesiredRuntimeState.RUNNING, profileId = VmProfileId("ubuntu-2404-arm64-uefi"), memoryMiB = 1024, vcpus = 2, dataDiskGiB = 8) },
        beginBootToken = { "b".repeat(43) },
        qemu = qemu,
        elapsedRealtimeMillis = elapsedRealtime,
        gracefulStopMillis = 10,
        forceExitMillis = 1_000,
    )

    private fun operationContext(step: String) = OperationContext(OperationId("op-qemu-test"), step, 1)

    private fun installArtifacts() {
        val root = File(context.filesDir, "nodehost-artifacts").apply { mkdirs() }
        listOf(
            "podroid-kernel", "podroid-initramfs", "podroid-alpine-squashfs",
            "ubuntu-2404-arm64-cloud", "aavmf-code", "aavmf-vars",
        ).forEach { id ->
            val bytes = "fixture-$id".toByteArray()
            File(root, id).writeBytes(bytes)
            val digest = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
            File(root, "$id.sha256").writeText("$digest\n")
        }
    }

    private class FakeQemuControl : QemuProcessControl {
        val exit = CompletableDeferred<QemuExit>()
        var shutdownRequests = 0
        var forceStops = 0
        override suspend fun start(plan: QemuLaunchPlan) = ManagedQemuProcess(42, { exit.await() }, { shutdownRequests++ })
        override fun forceStop() {
            forceStops++
            exit.complete(QemuExit(137, emptyList()))
        }
    }
}
