package org.nodehost.mesh

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.net.IpPrefix
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.system.OsConstants
import android.util.Log
import java.net.InetAddress
import java.util.UUID
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/** Headless adaptation of the official Tailscale Android IPNService/VpnService hooks. */
class NodeTailscaleVpnService : VpnService(), libtailscale.IPNService {
    private val serviceId = UUID.randomUUID().toString()
    @Volatile private var closed = false
    private val lifecycleScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                close()
                return START_NOT_STICKY
            }
            ACTION_START -> restartBudget.onExplicitStart()
            null -> if (!restartBudget.allowSystemRestart()) {
                stopSelf(startId)
                return START_NOT_STICKY
            }
            else -> return START_NOT_STICKY
        }
        if (prepare(this) != null) {
            stopSelf(startId)
            return START_NOT_STICKY
        }
        showForegroundNotification()
        return if (AndroidLibtailscaleRuntime.connectService(this)) START_STICKY else {
            stopSelf(startId)
            START_NOT_STICKY
        }
    }

    override fun id(): String = serviceId
    override fun protect(fd: Int): Boolean = super.protect(fd)
    override fun updateVpnStatus(active: Boolean) = Unit

    override fun newBuilder(): libtailscale.VPNServiceBuilder = AndroidVpnBuilder(
        Builder()
            .setSession("NodeHost mesh")
            .setBlocking(false)
            .allowFamily(OsConstants.AF_INET)
            .allowFamily(OsConstants.AF_INET6),
    )

    override fun disconnectVPN() {
        stopSelf()
    }

    override fun close() {
        if (closed) return
        closed = true
        AndroidLibtailscaleRuntime.disconnectService(this)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        close()
        super.onDestroy()
    }

    override fun onRevoke() {
        lifecycleScope.launch {
            try {
                AndroidLibtailscaleRuntime.revokeService(this@NodeTailscaleVpnService)
            } catch (failure: Exception) {
                Log.e("NodeHostMesh", "failed to clear wanted-running state after VPN revoke", failure)
            } finally {
                close()
            }
        }
        super.onRevoke()
    }

    private fun showForegroundNotification() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "NodeHost mesh", NotificationManager.IMPORTANCE_LOW),
        )
        val notification = Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle("NodeHost mesh")
            .setContentText("Host management VPN is active")
            .setOngoing(true)
            .build()
        startForeground(NOTIFICATION_ID, notification)
    }

    internal class AndroidVpnBuilder(private val builder: Builder) : libtailscale.VPNServiceBuilder {
        override fun setMTU(mtu: Int) { builder.setMtu(mtu) }
        override fun addDNSServer(server: String) { builder.addDnsServer(server) }
        override fun addSearchDomain(domain: String) { builder.addSearchDomain(domain) }
        override fun addRoute(address: String, prefixLength: Int) { builder.addRoute(address, prefixLength) }
        override fun addAddress(address: String, prefixLength: Int) { builder.addAddress(address, prefixLength) }
        override fun excludeRoute(address: String, prefixLength: Int) {
            check(Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) { "route exclusion requires API 33" }
            builder.excludeRoute(IpPrefix(InetAddress.getByName(address), prefixLength))
        }
        override fun establish(): libtailscale.ParcelFileDescriptor {
            val descriptor = builder.establish() ?: throw IllegalStateException("VPN permission was revoked")
            return DetachedParcelFileDescriptor(descriptor)
        }
    }

    internal class DetachedParcelFileDescriptor(
        private val descriptor: ParcelFileDescriptor,
    ) : libtailscale.ParcelFileDescriptor {
        override fun detach(): Int = descriptor.detachFd()
    }

    companion object {
        internal const val ACTION_START = "org.nodehost.mesh.START"
        internal const val ACTION_STOP = "org.nodehost.mesh.STOP"
        private const val CHANNEL_ID = "nodehost_mesh"
        private const val NOTIFICATION_ID = 1205
        private val restartBudget = VpnRestartBudget(3)
    }
}

internal class VpnRestartBudget(private val maximumConsecutiveRestarts: Int) {
    private var consecutiveRestarts = 0

    init { require(maximumConsecutiveRestarts in 1..10) }

    @Synchronized
    fun onExplicitStart() {
        consecutiveRestarts = 0
    }

    @Synchronized
    fun allowSystemRestart(): Boolean {
        consecutiveRestarts += 1
        return consecutiveRestarts <= maximumConsecutiveRestarts
    }
}
