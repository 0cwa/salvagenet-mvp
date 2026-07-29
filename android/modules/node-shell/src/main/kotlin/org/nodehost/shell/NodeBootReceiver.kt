package org.nodehost.shell

import android.content.*
import android.os.UserManager
import androidx.core.content.ContextCompat

class NodeBootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val unlocked = context.getSystemService(UserManager::class.java)?.isUserUnlocked == true
        if (!unlocked) return // stock MVP is secure-after-unlock
        ContextCompat.startForegroundService(context, Intent(context, NodeSupervisorService::class.java))
    }
}
