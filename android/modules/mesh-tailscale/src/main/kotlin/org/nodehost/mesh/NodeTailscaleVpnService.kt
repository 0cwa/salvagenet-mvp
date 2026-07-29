package org.nodehost.mesh

import android.content.Intent
import android.net.VpnService

/** Platform shell placeholder; T05 adapts the official IPNService lifecycle. */
class NodeTailscaleVpnService : VpnService() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY
}
