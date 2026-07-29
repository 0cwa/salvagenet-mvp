package org.nodehost.shell

import android.content.Context
import android.util.Log
import androidx.room.Room
import java.net.URI
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.nodehost.api.AcceptedOperationDispatcher
import org.nodehost.api.HostApiController
import org.nodehost.api.HostControlServer
import org.nodehost.core.ApplyRuntimeUseCase
import org.nodehost.core.Clock
import org.nodehost.core.RuntimeBackend
import org.nodehost.mesh.LibtailscaleHostMesh
import org.nodehost.store.NodeHostDatabase
import org.nodehost.store.RoomOperationRepository

/** Process composition root. Service lifecycle, rather than an Activity, owns the reconciliation actor. */
object NodeHostGraph {
    @Volatile private var components: Components? = null

    @Synchronized
    fun initialize(context: Context) {
        if (components != null) return
        val application = context.applicationContext
        val database = Room.databaseBuilder(application, NodeHostDatabase::class.java, "nodehost.db")
            .addMigrations(NodeHostDatabase.MIGRATION_1_2)
            .build()
        val clock = object : Clock {
            override fun epochMillis(): Long = System.currentTimeMillis()
        }
        val operations = RoomOperationRepository(database, clock)
        val bootstrap = AndroidGuestBootstrapStore(application)
        val runtime = AndroidQemuRuntimeBackend(
            application,
            desiredRuntime = { operations.loadDesiredRuntime(org.nodehost.model.RuntimeId.DEFAULT) },
            beginBootToken = bootstrap::beginBoot,
        )
        components = Components(
            application, database, operations, runtime, EncryptedEnrollmentRepository(application),
            LibtailscaleHostMesh(application), bootstrap, clock,
        )
    }

    internal fun createBootstrapServer(): BootstrapMetadataServer {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        return BootstrapMetadataServer(graph.bootstrap)
    }

    fun createSupervisor(scope: CoroutineScope): ReconciliationActor {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        graph.serviceScope = scope
        return ReconciliationActor(
            scope = scope,
            store = graph.operations,
            runtime = graph.runtime,
            events = { event ->
                when (event) {
                    is ReconciliationEvent.Failed -> Log.e(TAG, "reconciliation failed reason=${event.reason} class=${event.classification}")
                    is ReconciliationEvent.Completed -> Log.i(TAG, "reconciliation completed reason=${event.reason} steps=${event.plannedSteps}")
                    else -> Unit
                }
            },
        ).also { actor ->
            graph.reconciler = actor
            graph.runtime.attachLifecycle(scope) { actor.wake(WakeReason.RUNTIME_EVENT) }
            scope.launch {
                val enrollmentId = graph.enrollments.load()?.id?.value ?: return@launch
                if (graph.bootstrap.commit(enrollmentId)) actor.wake(WakeReason.SERVICE_STARTED)
            }
        }
    }

    suspend fun installEnrollment(
        rawEnrollment: ByteArray,
        rawGuestBootstrapSecret: ByteArray,
        idempotencyKey: String,
        approvedIssuerSpkiSha256: String,
    ): InstalledNode {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        val installed = EnrollmentInstaller(
            graph.enrollments, graph.operations, graph.mesh, graph.bootstrap,
            wakeReconciler = { graph.reconciler?.wake(WakeReason.DESIRED_STATE_CHANGED) },
            clock = graph.clock,
            isControllerRevoked = { ControllerRevocations.isRevoked(graph.database.openHelper.readableDatabase, it) },
        ).install(rawEnrollment, rawGuestBootstrapSecret, idempotencyKey, approvedIssuerSpkiSha256)
        startApi(graph, installed.controllerAuthenticator)
        return installed
    }

    fun restoreAuthorityAndApi() {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        val scope = checkNotNull(graph.serviceScope) { "supervisor service scope is not installed" }
        graph.apiStartJob?.cancel()
        graph.apiStartJob = scope.launch {
            val enrollment = graph.enrollments.load() ?: return@launch
            val authenticator = EnrolledControllerAuthenticator(
                enrollment.hostAccess.controllerCapability,
                enrollment.hostAccess.allowedControllerId,
                isRevoked = { ControllerRevocations.isRevoked(graph.database.openHelper.readableDatabase, it) },
            )
            val status = graph.mesh.status()
            if (status.state == org.nodehost.core.HostMeshStatus.State.STOPPED ||
                status.state == org.nodehost.core.HostMeshStatus.State.NEEDS_PERMISSION
            ) graph.mesh.start()
            startApi(graph, authenticator)
        }
    }

    suspend fun prepareDeviceTlsTrust(): String {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        val address = graph.mesh.status().addresses.firstNotNullOfOrNull { runCatching { TailnetBindAddress(it) }.getOrNull() }
        requireNotNull(address) { "tailnet address is not ready" }
        AndroidTlsCredentials.loadOrCreate(address.value)
        return AndroidTlsCredentials.spkiSha256()
    }

    /** Fail-closed local unenrollment: stop reachability before deleting every enrollment authority. */
    suspend fun unenroll() {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        graph.apiStartJob?.cancel()
        graph.apiServer?.stop()
        graph.apiServer = null
        graph.mesh.stop()
        graph.mesh.clearIdentity()
        graph.bootstrap.clear()
        graph.enrollments.clearAuthority()
        AndroidTlsCredentials.clear()
    }

    fun stopServiceOwnedComponents() {
        components?.run {
            apiStartJob?.cancel()
            apiServer?.stop()
            apiServer = null
            serviceScope = null
        }
    }

    private fun startApi(graph: Components, authenticator: org.nodehost.core.ControllerAuthenticator) {
        if (graph.apiServer != null) return
        val scope = checkNotNull(graph.serviceScope) { "supervisor service is not running" }
        graph.apiStartJob?.cancel()
        graph.apiStartJob = scope.launch {
            repeat(API_START_ATTEMPTS) { attempt ->
                val meshStatus = graph.mesh.status()
                val address = meshStatus.addresses.firstNotNullOfOrNull { raw -> runCatching { TailnetBindAddress(raw) }.getOrNull() }
                if (meshStatus.state == org.nodehost.core.HostMeshStatus.State.RUNNING && address != null) {
                    graph.enrollments.clearConsumedOneTimeCredentials()
                    val applyRuntime = ApplyRuntimeUseCase(graph.operations, SecureOperationIdFactory())
                    val mutations = AndroidHostMutations(
                        graph.application, graph.database, graph.operations, applyRuntime,
                        enrolledRepositoryOrigin = {
                            URI(requireNotNull(graph.enrollments.load()) { "enrollment authority unavailable" }.artifacts.repositoryUrl)
                        },
                        serviceScope = scope,
                    ).also(AndroidHostMutations::recoverInterruptedImports)
                    val controller = HostApiController(
                        authenticator,
                        AndroidHostResourceQueries(graph.application, graph.database, graph.operations, graph.mesh, graph.clock::epochMillis),
                        mutations,
                        applyRuntime,
                        LoopbackRecoverySshGateway(),
                        AcceptedOperationDispatcher {
                            val reconciler = checkNotNull(graph.reconciler) {
                                "reconciliation actor is unavailable"
                            }
                            check(reconciler.wake(WakeReason.DESIRED_STATE_CHANGED)) {
                                "reconciliation actor is unavailable"
                            }
                        },
                    )
                    val server = HostControlServer(controller, AndroidTlsCredentials.loadOrCreate(address.value))
                    runCatching { server.start(address.value, API_PORT) }
                        .onSuccess {
                            graph.apiServer?.stop()
                            graph.apiServer = server
                            Log.i(TAG, "Host API started on tailnet address port=$API_PORT")
                            return@launch
                        }
                        .onFailure { Log.w(TAG, "Host API start attempt ${attempt + 1} failed class=${it::class.java.simpleName}") }
                }
                delay(API_RETRY_MILLIS)
            }
            Log.e(TAG, "Host API did not obtain a tailnet bind address within retry budget")
        }
    }

    internal data class Components(
        val application: Context,
        val database: NodeHostDatabase,
        val operations: RoomOperationRepository,
        val runtime: AndroidQemuRuntimeBackend,
        val enrollments: EncryptedEnrollmentRepository,
        val mesh: LibtailscaleHostMesh,
        val bootstrap: AndroidGuestBootstrapStore,
        val clock: Clock,
        @Volatile var reconciler: ReconciliationActor? = null,
        @Volatile var serviceScope: CoroutineScope? = null,
        @Volatile var apiServer: HostControlServer? = null,
        @Volatile var apiStartJob: Job? = null,
    )

    private const val TAG = "NodeHostSupervisor"
    private const val API_PORT = 7443
    private const val API_START_ATTEMPTS = 30
    private const val API_RETRY_MILLIS = 2_000L
}
