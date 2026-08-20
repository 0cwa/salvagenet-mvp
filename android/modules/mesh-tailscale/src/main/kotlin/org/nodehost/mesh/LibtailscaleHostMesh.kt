package org.nodehost.mesh

import android.content.Context
import android.content.pm.ApplicationInfo
import android.net.VpnService
import java.net.URI
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.nodehost.core.HostMesh
import org.nodehost.core.HostMeshConfiguration
import org.nodehost.core.HostMeshStatus

/**
 * HostMesh policy around the pinned official Android libtailscale binding.
 *
 * VPN permission remains an Android UI decision: [start] reports NEEDS_PERMISSION and performs no
 * enrollment effect until the caller has completed [VpnService.prepare].
 */
class LibtailscaleHostMesh internal constructor(
    private val backend: HostMeshBackend,
    private val store: MeshConfigurationStore,
    private val hasVpnPermission: () -> Boolean,
    private val controlUrlPolicy: ControlUrlPolicy = ControlUrlPolicy.RELEASE,
    private val elapsedRealtimeMillis: () -> Long = android.os.SystemClock::elapsedRealtime,
    private val enrollmentTimeoutMillis: Long = DEFAULT_ENROLLMENT_TIMEOUT_MILLIS,
) : HostMesh {
    constructor(context: Context) : this(
        AndroidLibtailscaleRuntime.backend(context.applicationContext),
        AndroidMeshConfigurationStore(context.applicationContext),
        { VpnService.prepare(context.applicationContext) == null },
        ControlUrlPolicy.fromAndroid(context.applicationContext),
        android.os.SystemClock::elapsedRealtime,
        DEFAULT_ENROLLMENT_TIMEOUT_MILLIS,
    )

    private val operationLock = Mutex()
    private var current = HostMeshStatus(HostMeshStatus.State.STOPPED)
    private var enrollmentDeadlineElapsedRealtime: Long? = null

    override suspend fun configure(configuration: HostMeshConfiguration) = operationLock.withLock {
        require(current.state != HostMeshStatus.State.RUNNING && current.state != HostMeshStatus.State.ENROLLING) {
            "stop host mesh before reconfiguration"
        }
        val parsed = parseConfiguration(configuration)
        val previous = store.load()
        store.save(parsed)
        try {
            backend.configure(configuration)
            current = HostMeshStatus(
                if (hasVpnPermission()) HostMeshStatus.State.STOPPED else HostMeshStatus.State.NEEDS_PERMISSION,
            )
        } catch (failure: Exception) {
            try {
                if (previous == null) store.clear() else store.save(previous)
            } catch (restoreFailure: Exception) {
                failure.addSuppressed(restoreFailure)
            }
            current = failureStatus(failure)
            throw failure
        }
    }

    override suspend fun start() = operationLock.withLock {
        val configuration = store.load()
            ?: throw IllegalStateException("host mesh is not configured")
        try {
            validateControlUrl(configuration.controlUrl, controlUrlPolicy)
        } catch (failure: IllegalArgumentException) {
            current = failureStatus(failure)
            throw failure
        }
        if (!hasVpnPermission()) {
            current = HostMeshStatus(HostMeshStatus.State.NEEDS_PERMISSION, detail = "vpn_permission_required")
            return@withLock
        }
        try {
            require(enrollmentTimeoutMillis > 0) { "enrollment timeout must be positive" }
            backend.start(configuration.oneUseAuthKey)
            enrollmentDeadlineElapsedRealtime = elapsedRealtimeMillis() + enrollmentTimeoutMillis
            current = HostMeshStatus(HostMeshStatus.State.ENROLLING)
        } catch (failure: Exception) {
            enrollmentDeadlineElapsedRealtime = null
            current = failureStatus(failure)
            throw failure
        }
    }

    override suspend fun stop() = operationLock.withLock {
        try {
            backend.stop()
            enrollmentDeadlineElapsedRealtime = null
            current = HostMeshStatus(HostMeshStatus.State.STOPPED)
        } catch (failure: Exception) {
            current = failureStatus(failure)
            throw failure
        }
    }

    override suspend fun status(): HostMeshStatus = operationLock.withLock {
        if (current.state == HostMeshStatus.State.NEEDS_PERMISSION && !hasVpnPermission()) {
            return@withLock current
        }
        val observed = try {
            backend.snapshot()
        } catch (failure: Exception) {
            enrollmentDeadlineElapsedRealtime = null
            current = failureStatus(failure)
            return@withLock current
        }
        current = when (observed.state) {
            BackendMeshSnapshot.State.STOPPED -> {
                enrollmentDeadlineElapsedRealtime = null
                HostMeshStatus(HostMeshStatus.State.STOPPED)
            }
            BackendMeshSnapshot.State.ENROLLING -> {
                val deadline = enrollmentDeadlineElapsedRealtime
                    ?: (elapsedRealtimeMillis() + enrollmentTimeoutMillis).also { enrollmentDeadlineElapsedRealtime = it }
                if (elapsedRealtimeMillis() >= deadline) {
                    HostMeshStatus(HostMeshStatus.State.ERROR, detail = "enrollment_not_completed")
                } else {
                    HostMeshStatus(HostMeshStatus.State.ENROLLING)
                }
            }
            BackendMeshSnapshot.State.ERROR -> {
                enrollmentDeadlineElapsedRealtime = null
                HostMeshStatus(
                    HostMeshStatus.State.ERROR,
                    detail = observed.failure?.take(MAX_FAILURE_DETAIL_LENGTH) ?: "libtailscale_failure",
                )
            }
            BackendMeshSnapshot.State.RUNNING -> {
                enrollmentDeadlineElapsedRealtime = null
                try {
                    // Enrollment is confirmed by libtailscale before the one-use key is erased.
                    store.deleteOneUseAuthKey()
                    HostMeshStatus(
                        HostMeshStatus.State.RUNNING,
                        addresses = observed.addresses.take(MAX_ADDRESSES),
                    )
                } catch (_: Exception) {
                    HostMeshStatus(HostMeshStatus.State.ERROR, detail = "auth_key_deletion_failed")
                }
            }
        }
        current
    }

    override suspend fun clearIdentity() = operationLock.withLock {
        try {
            backend.logout()
            var keyDeletionFailure: Exception? = null
            try {
                // Remove one-use material first so a later configuration-clear failure cannot retain it.
                store.deleteOneUseAuthKey()
            } catch (failure: Exception) {
                keyDeletionFailure = failure
            }
            try {
                store.clear()
            } catch (failure: Exception) {
                keyDeletionFailure?.let(failure::addSuppressed)
                throw failure
            }
            enrollmentDeadlineElapsedRealtime = null
            current = HostMeshStatus(HostMeshStatus.State.STOPPED)
        } catch (failure: Exception) {
            current = failureStatus(failure)
            throw failure
        }
    }

    private fun parseConfiguration(configuration: HostMeshConfiguration): PersistedMeshConfiguration {
        require(configuration.controlUrl.length <= MAX_CONTROL_URL_LENGTH) { "control URL is too long" }
        validateControlUrl(configuration.controlUrl, controlUrlPolicy)
        require(HOSTNAME.matches(configuration.hostname)) { "invalid mesh hostname" }
        val authKey = configuration.oneUseAuthKey.value
        require(authKey.length in 16..512 && !authKey.any(Char::isWhitespace)) { "invalid one-use auth key" }
        return PersistedMeshConfiguration(configuration.controlUrl, configuration.hostname, authKey)
    }

    private fun failureStatus(failure: Exception) = HostMeshStatus(
        HostMeshStatus.State.ERROR,
        detail = failure::class.java.simpleName.take(MAX_FAILURE_DETAIL_LENGTH),
    )

    private companion object {
        const val MAX_CONTROL_URL_LENGTH = 2048
        const val MAX_ADDRESSES = 16
        const val MAX_FAILURE_DETAIL_LENGTH = 128
        const val DEFAULT_ENROLLMENT_TIMEOUT_MILLIS = 120_000L
        val HOSTNAME = Regex("[a-z0-9][a-z0-9-]{0,62}")
    }
}

/** Process policy only: enrollment data cannot opt into cleartext control traffic. */
internal class ControlUrlPolicy private constructor(val allowCleartextForDebugLab: Boolean) {
    companion object {
        val RELEASE = ControlUrlPolicy(allowCleartextForDebugLab = false)
        val DEBUG_LAB = ControlUrlPolicy(allowCleartextForDebugLab = true)

        fun fromAndroid(context: Context): ControlUrlPolicy = fromApplicationFlags(context.applicationInfo.flags)

        internal fun fromApplicationFlags(applicationFlags: Int): ControlUrlPolicy =
            if (applicationFlags and ApplicationInfo.FLAG_DEBUGGABLE != 0) DEBUG_LAB else RELEASE
    }
}

internal fun validateControlUrl(controlUrl: String, policy: ControlUrlPolicy) {
    val uri = URI(controlUrl)
    require(uri.scheme == "https" || (uri.scheme == "http" && policy.allowCleartextForDebugLab)) {
        "control URL must use HTTPS"
    }
    require(!uri.host.isNullOrBlank() && uri.userInfo == null && uri.query == null && uri.fragment == null) {
        "control URL must be an absolute server URL"
    }
}
