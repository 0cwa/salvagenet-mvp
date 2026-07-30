package org.nodehost.shell

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import java.io.File
import java.io.RandomAccessFile
import java.security.MessageDigest
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertArrayEquals
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
        File(context.filesDir, "nodehost-durable").deleteRecursively()
        scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        installArtifacts()
    }

    @After fun tearDown() {
        scope.cancel()
        File(context.filesDir, "nodehost-artifacts").deleteRecursively()
        File(context.filesDir, "vms").deleteRecursively()
        File(context.filesDir, "nodehost-durable").deleteRecursively()
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

    @Test fun nonPodroidBareArtifactCannotBypassActiveManifestContract() {
        val root = File(context.filesDir, "nodehost-artifacts")
        val manifest = ArtifactManifestStore(root).active("aavmf-code")!!
        val bytes = ArtifactManifestStore(root).payload(manifest).readBytes()
        assertTrue(File(root, "aavmf-code.manifest.json").delete())
        File(root, "aavmf-code").writeBytes(bytes)
        File(root, "aavmf-code.sha256").writeText("${manifest.sha256}\n")

        val failure = runCatching {
            backend(FakeQemuControl()).profile(VmProfileId("ubuntu-2404-arm64-uefi"), true)
        }.exceptionOrNull()

        assertTrue(failure?.message.orEmpty().contains("active artifact manifest is required: aavmf-code"))
    }

    @Test fun mutableSystemStateSurvivesRepeatedPreparationAfterBootstrapConsumption() = runBlocking {
        val backend = backend(FakeQemuControl())
        backend.execute(operationContext("prepare-1"), RuntimeStep.PrepareDisks)
        val instance = File(context.filesDir, "vms/default")
        val systemMutation = "mutated-system".toByteArray()
        val varsMutation = "mutated-vars".toByteArray()
        File(instance, "system.qcow2").writeBytes(systemMutation)
        File(instance, "firmware-vars.fd").writeBytes(varsMutation)

        backend.execute(operationContext("prepare-2"), RuntimeStep.PrepareDisks)

        assertArrayEquals(systemMutation, File(instance, "system.qcow2").readBytes())
        assertArrayEquals(varsMutation, File(instance, "firmware-vars.fd").readBytes())
    }

    @Test fun preservedDataMovesOutBeforeDeleteAndReattachesOnRecreate() = runBlocking {
        val runtime = testRuntime(preserveData = true)
        val backend = backend(FakeQemuControl(), runtime = runtime)
        backend.execute(operationContext("prepare"), RuntimeStep.PrepareDisks)
        val data = File(context.filesDir, "vms/default/data.raw")
        RandomAccessFile(data, "rw").use { it.seek(7); it.write(byteArrayOf(42)) }

        backend.execute(operationContext("remove"), RuntimeStep.RemoveSystem)
        assertFalse(File(context.filesDir, "vms/default").exists())
        assertTrue(File(context.filesDir, "nodehost-durable/vms/default/data.raw").isFile)
        backend.execute(operationContext("recreate"), RuntimeStep.PrepareDisks)
        RandomAccessFile(data, "r").use { it.seek(7); assertEquals(42, it.read()) }
    }

    @Test fun failedDataMoveAbortsDeletion() = runBlocking {
        val backend = backend(FakeQemuControl(), runtime = testRuntime(preserveData = true), move = { _, _ -> error("move failed") })
        backend.execute(operationContext("prepare"), RuntimeStep.PrepareDisks)
        assertTrue(runCatching { backend.execute(operationContext("remove"), RuntimeStep.RemoveSystem) }.isFailure)
        assertTrue(File(context.filesDir, "vms/default/system.qcow2").isFile)
        assertTrue(File(context.filesDir, "vms/default/data.raw").isFile)
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

    @Test fun runningObservationRetainsPreparedGenerationWhenDesiredChanges() = runBlocking {
        var desired = testRuntime()
        val qemu = FakeQemuControl()
        val backend = AndroidQemuRuntimeBackend(
            context,
            desiredRuntime = { desired },
            beginBootToken = { "b".repeat(43) },
            recoveryPort = org.nodehost.qemu.RecoverySshHostPort(19922),
            qemu = qemu,
        )
        backend.attachLifecycle(scope) {}
        backend.execute(operationContext("prepare"), RuntimeStep.PrepareBoot)
        backend.execute(operationContext("start"), RuntimeStep.StartProcess)
        desired = testRuntime().copy(generation = 2, profileId = VmProfileId("k3s-worker-lab"), memoryMiB = 2048)
        File(context.filesDir, "vms/default").mkdirs()
        File(context.filesDir, "vms/default/qmp.sock").createNewFile()
        backend.execute(operationContext("qmp"), RuntimeStep.WaitForQmp)
        assertEquals(1, qemu.qmpReadinessChecks)

        val running = backend.observe(RuntimeId.DEFAULT) as RuntimeObservation.Running
        assertEquals(1L, running.appliedGeneration)
        assertEquals(1L, qemu.startedRuntimes.single().generation)

        qemu.exit.complete(QemuExit(0, emptyList()))
        withTimeout(2_000) { while (backend.observe(RuntimeId.DEFAULT) is RuntimeObservation.Running) kotlinx.coroutines.yield() }
        assertTrue(backend.observe(RuntimeId.DEFAULT) !is RuntimeObservation.Running)
    }

    @Test fun qmpSocketWithoutRunningMonitorDoesNotCountAsReadiness() = runBlocking {
        val qemu = FakeQemuControl().apply { qmpStatus = "paused" }
        val backend = backend(qemu)
        backend.attachLifecycle(scope) {}
        backend.execute(operationContext("prepare"), RuntimeStep.PrepareBoot)
        backend.execute(operationContext("start"), RuntimeStep.StartProcess)
        File(context.filesDir, "vms/default").mkdirs()
        File(context.filesDir, "vms/default/qmp.sock").createNewFile()

        val result = runCatching { backend.execute(operationContext("qmp"), RuntimeStep.WaitForQmp) }

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("not running"))
        assertEquals(1, qemu.qmpReadinessChecks)
        assertTrue(backend.observe(RuntimeId.DEFAULT) is RuntimeObservation.Starting)
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
        runtime: RuntimeSpec = testRuntime(),
        move: (File, File) -> Unit = { source, target -> java.nio.file.Files.move(source.toPath(), target.toPath(), java.nio.file.StandardCopyOption.ATOMIC_MOVE) },
    ) = AndroidQemuRuntimeBackend(
        context,
        desiredRuntime = { runtime },
        beginBootToken = { "b".repeat(43) },
        recoveryPort = org.nodehost.qemu.RecoverySshHostPort(19922),
        qemu = qemu,
        elapsedRealtimeMillis = elapsedRealtime,
        gracefulStopMillis = 10,
        forceExitMillis = 1_000,
        atomicMove = move,
    )

    private fun testRuntime(preserveData: Boolean = false) = RuntimeSpec(
        generation = 1, desiredState = DesiredRuntimeState.RUNNING,
        profileId = VmProfileId("ubuntu-2404-arm64-uefi"), memoryMiB = 1024,
        vcpus = 2, dataDiskGiB = 8, preserveDataOnDelete = preserveData,
    )

    private fun operationContext(step: String) = OperationContext(OperationId("op-qemu-test"), step, 1)

    private fun installArtifacts() {
        val root = File(context.filesDir, "nodehost-artifacts").apply { mkdirs() }
        listOf(
            "podroid-kernel", "podroid-initramfs", "podroid-alpine-squashfs",
        ).forEach { id ->
            val bytes = "fixture-$id".toByteArray()
            File(root, id).writeBytes(bytes)
            File(root, "$id.sha256").writeText("${sha256(bytes)}\n")
        }
        val manifests = ArtifactManifestStore(root)
        listOf(
            "ubuntu-2404-arm64-cloud", "aavmf-code", "aavmf-vars",
        ).forEach { id ->
            val bytes = "fixture-$id".toByteArray()
            val digest = sha256(bytes)
            val payload = manifests.versionPayload(id, digest)
            payload.parentFile!!.mkdirs()
            payload.writeBytes(bytes)
            manifests.writeActive(ArtifactManifest(id, digest, bytes.size.toLong()), "test")
        }
    }

    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }

    private class FakeQemuControl : QemuProcessControl {
        val exit = CompletableDeferred<QemuExit>()
        val startedRuntimes = mutableListOf<RuntimeSpec>()
        var qmpStatus = "running"
        var qmpReadinessChecks = 0
        var shutdownRequests = 0
        var forceStops = 0
        override suspend fun start(plan: QemuLaunchPlan, runtime: RuntimeSpec): ManagedQemuProcess {
            startedRuntimes += runtime
            return ManagedQemuProcess(42, { exit.await() }, { qmpReadinessChecks++; qmpStatus }, { shutdownRequests++ })
        }
        override fun forceStop() {
            forceStops++
            exit.complete(QemuExit(137, emptyList()))
        }
    }
}
