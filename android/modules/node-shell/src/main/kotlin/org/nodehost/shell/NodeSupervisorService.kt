package org.nodehost.shell

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat

class NodeSupervisorService : Service() {
    override fun onCreate() { super.onCreate(); NodeHostGraph.initialize(this); createChannel() }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = NotificationCompat.Builder(this, CHANNEL).setSmallIcon(android.R.drawable.stat_notify_sync).setContentTitle("NodeHost").setContentText("Reconciling desired node state").setOngoing(true).build()
        val type = if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0
        ServiceCompat.startForeground(this, ID, notification, type)
        // TODO(MVP-HARDENING, T03): send a typed wake reason to the single reconciler actor.
        return START_STICKY
    }
    override fun onTaskRemoved(rootIntent: Intent?) { /* UI task removal is not a runtime stop command. */ }
    override fun onBind(intent: Intent?): IBinder? = null
    private fun createChannel() { if (Build.VERSION.SDK_INT >= 26) getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(CHANNEL, "Node hosting", NotificationManager.IMPORTANCE_LOW)) }
    companion object { const val CHANNEL="nodehost-runtime"; const val ID=47001 }
}
