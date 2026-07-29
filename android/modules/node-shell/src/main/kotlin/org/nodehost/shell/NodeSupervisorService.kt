package org.nodehost.shell

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel

class NodeSupervisorService : Service() {
    private lateinit var supervisorScope: CoroutineScope
    private lateinit var reconciler: ReconciliationActor

    override fun onCreate() {
        super.onCreate()
        NodeHostGraph.initialize(this)
        createChannel()
        supervisorScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        reconciler = NodeHostGraph.createSupervisor(supervisorScope)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle("NodeHost")
            .setContentText("Reconciling desired node state")
            .setOngoing(true)
            .build()
        val type = if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0
        ServiceCompat.startForeground(this, ID, notification, type)
        reconciler.wake(WakeReason.SERVICE_STARTED)
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // A UI lifecycle event is deliberately not forwarded as a desired-state command.
    }

    override fun onDestroy() {
        // The pending intent is durable. Cancellation leaves it recoverable by the sticky restart.
        reconciler.close()
        supervisorScope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel(CHANNEL, "Node hosting", NotificationManager.IMPORTANCE_LOW),
            )
        }
    }

    companion object {
        const val CHANNEL = "nodehost-runtime"
        const val ID = 47001
    }
}
