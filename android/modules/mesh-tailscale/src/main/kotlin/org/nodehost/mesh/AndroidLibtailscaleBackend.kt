package org.nodehost.mesh

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.net.ConnectivityManager
import android.net.LinkProperties
import android.net.Network
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.core.content.ContextCompat
import java.io.ByteArrayInputStream
import java.net.NetworkInterface
import java.util.Collections
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import libtailscale.Application
import libtailscale.Libtailscale
import org.json.JSONArray
import org.json.JSONObject
import org.nodehost.core.HostMeshConfiguration

/** Process singleton required by libtailscale's single Android backend and VPN service hooks. */
internal object AndroidLibtailscaleRuntime {
    private val lock = Any()
    @Volatile private var instance: AndroidLibtailscaleBackend? = null

    fun backend(context: Context): AndroidLibtailscaleBackend = instance ?: synchronized(lock) {
        instance ?: AndroidLibtailscaleBackend(context.applicationContext).also { instance = it }
    }

    fun connectService(service: NodeTailscaleVpnService): Boolean =
        backend(service.applicationContext).connectService(service)

    fun disconnectService(service: NodeTailscaleVpnService) {
        instance?.disconnectService(service)
    }

    suspend fun revokeService(service: NodeTailscaleVpnService) {
        val context = service.applicationContext
        revokeVpn(
            stopBackend = { backend(context).stopForRevocation() },
            deleteOneUseAuthKey = { AndroidMeshConfigurationStore(context).deleteOneUseAuthKey() },
        )
    }
}

internal class AndroidLibtailscaleBackend(private val context: Context) : HostMeshBackend {
    private val secureState = AndroidSecureState(context)
    private val controlUrlPolicy = ControlUrlPolicy.fromAndroid(context)
    private val platformContext by lazy { AndroidPlatformContext(context, secureState) }
    private val application: Application by lazy(LazyThreadSafetyMode.SYNCHRONIZED) {
        val stateDirectory = context.filesDir.resolve("mesh-tailscale").apply { mkdirs() }
        Libtailscale.start(
            stateDirectory.absolutePath,
            "",
            false,
            platformContext,
        ).also {
            platformContext.startNetworkMonitoring()
            it.setClientLoggingEnabled(false)
        }
    }

    private val localApi by lazy { OfficialLocalApiClient { application } }

    override suspend fun configure(configuration: HostMeshConfiguration) {
        localApi.execute(OfficialLocalApiRequests.configure(configuration, controlUrlPolicy))
    }

    override suspend fun start(oneUseAuthKey: String?) {
        localApi.execute(OfficialLocalApiRequests.start(oneUseAuthKey))
        ContextCompat.startForegroundService(
            context,
            Intent(context, NodeTailscaleVpnService::class.java).setAction(NodeTailscaleVpnService.ACTION_START),
        )
    }

    override suspend fun stop() {
        stopForRevocation()
        context.startService(
            Intent(context, NodeTailscaleVpnService::class.java).setAction(NodeTailscaleVpnService.ACTION_STOP),
        )
    }

    suspend fun stopForRevocation() {
        localApi.execute(OfficialLocalApiRequests.stop())
    }

    override suspend fun snapshot(): BackendMeshSnapshot {
        val json = JSONObject(String(localApi.execute(LocalApiCall("GET", "status"))))
        val backendState = json.optString("BackendState")
        val addresses = json.optJSONArray("TailscaleIPs")?.let { values ->
            buildList {
                for (index in 0 until minOf(values.length(), MAX_ADDRESSES)) {
                    values.optString(index).takeIf { it.length in 2..64 }?.let(::add)
                }
            }
        }.orEmpty()
        return when (backendState) {
            "Running" -> BackendMeshSnapshot(BackendMeshSnapshot.State.RUNNING, addresses)
            "Starting", "NeedsLogin", "NeedsMachineAuth" -> BackendMeshSnapshot(BackendMeshSnapshot.State.ENROLLING)
            "Stopped", "NoState", "" -> BackendMeshSnapshot(BackendMeshSnapshot.State.STOPPED)
            else -> BackendMeshSnapshot(BackendMeshSnapshot.State.ERROR, failure = "backend_state_unrecognized")
        }
    }

    override suspend fun logout() {
        localApi.execute(LocalApiCall("POST", "logout"))
        secureState.clearNames(secureState.names(LIBTAILSCALE_STATE_PREFIX))
    }

    fun connectService(service: NodeTailscaleVpnService): Boolean = try {
        application // Ensure official encrypted state is restored before attaching the VPN facade.
        Libtailscale.requestVPN(service)
        true
    } catch (failure: Exception) {
        logClassifiedFailure("libtailscale VPN attach failed", failure)
        false
    }

    fun disconnectService(service: NodeTailscaleVpnService) {
        try {
            Libtailscale.serviceDisconnect(service)
        } catch (failure: Exception) {
            logClassifiedFailure("libtailscale VPN detach failed", failure)
        }
    }

    private fun logClassifiedFailure(message: String, failure: Exception) {
        Log.e(TAG, "$message (${failure::class.java.simpleName.take(64)})")
    }

    private companion object {
        const val TAG = "NodeHostMesh"
        const val LIBTAILSCALE_STATE_PREFIX = "libtailscale."
        const val MAX_ADDRESSES = 16
    }
}

internal suspend fun revokeVpn(
    stopBackend: suspend () -> Unit,
    deleteOneUseAuthKey: suspend () -> Unit,
) {
    stopBackend()
    deleteOneUseAuthKey()
}

internal data class LocalApiCall(val method: String, val endpoint: String, val body: ByteArray? = null)

internal object OfficialLocalApiRequests {
    fun configure(configuration: HostMeshConfiguration, controlUrlPolicy: ControlUrlPolicy): LocalApiCall {
        validateControlUrl(configuration.controlUrl, controlUrlPolicy)
        return LocalApiCall(
            "PATCH",
            "prefs",
            JSONObject()
                .put("ControlURL", configuration.controlUrl)
                .put("ControlURLSet", true)
                .put("Hostname", configuration.hostname)
                .put("HostnameSet", true)
                .toString()
                .toByteArray(),
        )
    }

    fun start(oneUseAuthKey: String?): LocalApiCall {
        val options = JSONObject()
        oneUseAuthKey?.let { options.put("AuthKey", it) }
        return LocalApiCall("POST", "start", options.toString().toByteArray())
    }

    fun stop() = LocalApiCall(
        "PATCH",
        "prefs",
        JSONObject()
            .put("WantRunning", false)
            .put("WantRunningSet", true)
            .toString()
            .toByteArray(),
    )
}

internal class OfficialLocalApiClient(private val application: () -> Application) {
    suspend fun execute(call: LocalApiCall): ByteArray = withContext(Dispatchers.IO) {
        require(call.body == null || call.body.size <= MAX_REQUEST_BYTES)
        val response = application().callLocalAPI(
            LOCAL_API_TIMEOUT_MILLIS,
            call.method,
            "/localapi/v0/${call.endpoint}",
            call.body?.let(::ByteArrayGoInputStream),
        )
        val responseBody = response.bodyBytes() ?: ByteArray(0)
        check(responseBody.size <= MAX_RESPONSE_BYTES) { "libtailscale response exceeded limit" }
        check(response.statusCode() in 200..299) { "libtailscale LocalAPI status ${response.statusCode()}" }
        responseBody
    }

    private companion object {
        const val LOCAL_API_TIMEOUT_MILLIS = 5_000L
        const val MAX_REQUEST_BYTES = 4 * 1024
        const val MAX_RESPONSE_BYTES = 64 * 1024
    }
}

internal class ByteArrayGoInputStream(bytes: ByteArray) : libtailscale.InputStream {
    private val input = ByteArrayInputStream(bytes)
    override fun read(): ByteArray = ByteArray(MAX_READ_BYTES).let { buffer ->
        val count = input.read(buffer)
        if (count < 0) ByteArray(0) else buffer.copyOf(count)
    }
    override fun close() = input.close()

    private companion object { const val MAX_READ_BYTES = 8 * 1024 }
}

private class AndroidPlatformContext(
    private val context: Context,
    private val secureState: AndroidSecureState,
) : libtailscale.AppContext {
    private val nativeLog = NativeLogCallback(
        diagnosticsEnabled = context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0,
        sink = { message -> Log.d("NodeHostMesh/libtailscale", message) },
    )
    private val connectivityManager = context.getSystemService(ConnectivityManager::class.java)
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) = notifyNetworkChanged(network)
        override fun onLinkPropertiesChanged(network: Network, linkProperties: LinkProperties) =
            notifyNetworkChanged(network, linkProperties)
        override fun onLost(network: Network) = notifyNetworkChanged(network)
    }
    @Volatile private var monitoringStarted = false

    @Synchronized
    fun startNetworkMonitoring() {
        if (monitoringStarted) return
        connectivityManager.registerDefaultNetworkCallback(networkCallback)
        monitoringStarted = true
    }

    private fun notifyNetworkChanged(network: Network, properties: LinkProperties? = null) {
        val interfaceName = properties?.interfaceName
            ?: connectivityManager.getLinkProperties(network)?.interfaceName
            ?: ""
        try {
            Libtailscale.onDNSConfigChanged(interfaceName)
        } catch (failure: Exception) {
            Log.w(TAG, "libtailscale network callback failed (${failure::class.java.simpleName.take(64)})")
        }
    }
    override fun log(tag: String?, line: String?) = nativeLog.emit(line)
    override fun encryptToPref(key: String, value: String) = secureState.put(STATE_PREFIX + key, value)
    override fun decryptFromPref(key: String): String? = secureState.get(STATE_PREFIX + key)
    override fun getStateStoreKeysJSON(): String = JSONArray(
        secureState.names(STATE_PREFIX + "statestore-").map { it.removePrefix(STATE_PREFIX + "statestore-") },
    ).toString()
    override fun getOSVersion(): String = Build.VERSION.RELEASE
    override fun getSDKInt(): Long = Build.VERSION.SDK_INT.toLong()
    override fun getDeviceName(): String = "${Build.MANUFACTURER} ${Build.MODEL}".take(128)
    @Suppress("DEPRECATION")
    override fun getInstallSource(): String = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
        context.packageManager.getInstallSourceInfo(context.packageName).installingPackageName.orEmpty()
    } else {
        context.packageManager.getInstallerPackageName(context.packageName).orEmpty()
    }
    override fun shouldUseGoogleDNSFallback(): Boolean = false
    override fun isChromeOS(): Boolean = context.packageManager.hasSystemFeature("org.chromium.arc")
    override fun isClientLoggingEnabled(): Boolean = false

    override fun getInterfacesAsJson(): String {
        val result = JSONArray()
        val interfaces = NetworkInterface.getNetworkInterfaces() ?: return result.toString()
        for (network in Collections.list(interfaces).take(MAX_INTERFACES)) {
            val item = JSONObject()
                .put("name", network.name.take(64))
                .put("index", network.index)
                .put("mtu", network.mtu)
                .put("up", network.isUp)
                .put("broadcast", !network.isPointToPoint)
                .put("loopback", network.isLoopback)
                .put("pointToPoint", network.isPointToPoint)
                .put("multicast", network.supportsMulticast())
            val addresses = JSONArray()
            network.interfaceAddresses.take(MAX_INTERFACE_ADDRESSES).forEach { address ->
                addresses.put(
                    JSONObject()
                        .put("ip", address.address.hostAddress.orEmpty().substringBefore('%'))
                        .put("prefixLen", address.networkPrefixLength.toInt()),
                )
            }
            result.put(item.put("addrs", addresses))
        }
        return result.toString()
    }

    override fun getPlatformDNSConfig(): String {
        val network = connectivityManager.activeNetwork ?: return ""
        val properties = connectivityManager.getLinkProperties(network) ?: return ""
        val servers = properties.dnsServers.joinToString(" ") { it.hostAddress.orEmpty() }
        return "$servers\n${properties.domains.orEmpty()}".trim()
    }
    override fun getSyspolicyStringValue(key: String?): String = ""
    override fun getSyspolicyBooleanValue(key: String?): Boolean = false
    override fun getSyspolicyStringArrayJSONValue(key: String?): String = "[]"
    override fun hardwareAttestationKeySupported(): Boolean = false
    override fun hardwareAttestationKeyCreate(): String = throw UnsupportedOperationException("hardware attestation disabled")
    override fun hardwareAttestationKeyRelease(id: String?) = throw UnsupportedOperationException("hardware attestation disabled")
    override fun hardwareAttestationKeyPublic(id: String?): ByteArray = throw UnsupportedOperationException("hardware attestation disabled")
    override fun hardwareAttestationKeySign(id: String?, data: ByteArray?): ByteArray = throw UnsupportedOperationException("hardware attestation disabled")
    override fun hardwareAttestationKeyLoad(id: String?) = throw UnsupportedOperationException("hardware attestation disabled")
    override fun getUserCACertsPEM(): ByteArray = ByteArray(0)

    override fun bindSocketToNetwork(fd: Int): Boolean = try {
        val network = connectivityManager.activeNetwork ?: return false
        ParcelFileDescriptor.fromFd(fd).use { network.bindSocket(it.fileDescriptor) }
        true
    } catch (failure: Exception) {
        Log.w(TAG, "socket protection failed (${failure::class.java.simpleName.take(64)})")
        false
    }

    private companion object {
        const val TAG = "NodeHostMesh"
        const val STATE_PREFIX = "libtailscale."
        const val MAX_INTERFACES = 64
        const val MAX_INTERFACE_ADDRESSES = 32
    }
}

/** Release callbacks are silent; debug callbacks expose only bounded, redacted diagnostics. */
internal class NativeLogCallback(
    private val diagnosticsEnabled: Boolean,
    private val sink: (String) -> Unit,
) {
    fun emit(line: String?) {
        if (!diagnosticsEnabled) return
        var redacted = line.orEmpty().take(MAX_INPUT_CHARS)
        redacted = URL.replace(redacted, "[URL_REDACTED]")
        redacted = AUTHORIZATION.replace(redacted) { "${it.groupValues[1]}[REDACTED]" }
        redacted = BEARER.replace(redacted) { "${it.groupValues[1]}[REDACTED]" }
        redacted = AUTH_KEY.replace(redacted, "[AUTH_KEY_REDACTED]")
        redacted = CREDENTIAL.replace(redacted) { "${it.groupValues[1]}[REDACTED]" }
        sink(redacted.take(MAX_OUTPUT_CHARS))
    }

    private companion object {
        const val MAX_INPUT_CHARS = 4 * 1024
        const val MAX_OUTPUT_CHARS = 1024
        val URL = Regex("(?i)\\b(?:https?|wss?)://[^\\s\\]}>]+")
        val AUTHORIZATION = Regex("(?i)(\\bauthorization\\s*[:=]\\s*)(?:bearer|basic)?\\s*[^\\s,;]+")
        val BEARER = Regex("(?i)(\\bbearer\\s+)[^\\s,;]+")
        val AUTH_KEY = Regex("(?i)\\btskey-(?:auth|client)-[a-z0-9_-]+")
        val CREDENTIAL = Regex(
            "(?i)([\\\"']?\\b(?:auth|auth[_-]?key|api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|pwd|secret|credential)\\b[\\\"']?\\s*[:=]\\s*[\\\"']?)[^\\s,;\\\"']+",
        )
    }
}
