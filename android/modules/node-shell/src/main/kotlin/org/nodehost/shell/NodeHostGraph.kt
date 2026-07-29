package org.nodehost.shell

import android.content.Context
import android.util.Log
import androidx.room.Room
import kotlinx.coroutines.CoroutineScope
import org.nodehost.core.Clock
import org.nodehost.core.OperationContext
import org.nodehost.core.RuntimeBackend
import org.nodehost.core.StepOutcome
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation
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
        components = Components(database, UnavailableRuntimeBackend)
    }

    fun createSupervisor(scope: CoroutineScope): ReconciliationActor {
        val graph = checkNotNull(components) { "NodeHostGraph is not initialized" }
        val clock = object : Clock {
            override fun epochMillis(): Long = System.currentTimeMillis()
        }
        return ReconciliationActor(
            scope = scope,
            store = RoomOperationRepository(graph.database, clock),
            runtime = graph.runtime,
            events = { event ->
                when (event) {
                    is ReconciliationEvent.Failed -> Log.e(TAG, "reconciliation failed reason=${event.reason} class=${event.classification}")
                    is ReconciliationEvent.Completed -> Log.i(TAG, "reconciliation completed reason=${event.reason} steps=${event.plannedSteps}")
                    else -> Unit
                }
            },
        )
    }

    internal data class Components(val database: NodeHostDatabase, val runtime: RuntimeBackend)

    private object UnavailableRuntimeBackend : RuntimeBackend {
        override suspend fun observe(id: RuntimeId): RuntimeObservation =
            RuntimeObservation.Unknown(id, "QEMU runtime adapter is not composed yet")

        override suspend fun execute(context: OperationContext, step: org.nodehost.core.RuntimeStep): StepOutcome =
            error("QEMU runtime adapter is not composed yet")
    }

    private const val TAG = "NodeHostSupervisor"
}
