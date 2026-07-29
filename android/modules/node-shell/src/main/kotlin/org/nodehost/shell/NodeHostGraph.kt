package org.nodehost.shell

import android.content.Context
import android.util.Log
import androidx.room.Room
import kotlinx.coroutines.CoroutineScope
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
            bootstrapToken = bootstrap::bootstrapToken,
        )
        components = Components(
            database, operations, runtime, EncryptedEnrollmentRepository(application),
            LibtailscaleHostMesh(application), bootstrap, clock,
        )
    }

    fun createBootstrapServer(): BootstrapMetadataServer {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        return BootstrapMetadataServer(graph.bootstrap)
    }

    fun createSupervisor(scope: CoroutineScope): ReconciliationActor {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
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
        ).also { graph.reconciler = it }
    }

    suspend fun installEnrollment(
        rawEnrollment: ByteArray,
        guestMesh: GuestMeshBootstrap,
        idempotencyKey: String,
    ): InstalledNode {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        return EnrollmentInstaller(
            graph.enrollments, graph.operations, graph.mesh, graph.bootstrap,
            wakeReconciler = { graph.reconciler?.wake(WakeReason.DESIRED_STATE_CHANGED) },
            clock = graph.clock,
        ).install(rawEnrollment, guestMesh, idempotencyKey)
    }

    internal data class Components(
        val database: NodeHostDatabase,
        val operations: RoomOperationRepository,
        val runtime: RuntimeBackend,
        val enrollments: EncryptedEnrollmentRepository,
        val mesh: LibtailscaleHostMesh,
        val bootstrap: AndroidGuestBootstrapStore,
        val clock: Clock,
        @Volatile var reconciler: ReconciliationActor? = null,
    )

    private const val TAG = "NodeHostSupervisor"
}
