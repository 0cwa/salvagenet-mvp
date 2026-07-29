package org.nodehost.mesh

import android.content.Context
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
) : HostMesh {
    constructor(context: Context) : this(
        AndroidLibtailscaleRuntime.backend(context.applicationContext),
        AndroidMeshConfigurationStore(context.applicationContext),
        { VpnService.prepare(context.applicationContext) == null },
    )

    private val operationLock = Mutex()
    private var current = HostMeshStatus(HostMeshStatus.State.STOPPED)
    private var enrollmentObservations = 0

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
        if (!hasVpnPermission()) {
            current = HostMeshStatus(HostMeshStatus.State.NEEDS_PERMISSION, detail = "vpn_permission_required")
            return@withLock
        }
        try {
            backend.start(configuration.oneUseAuthKey)
            enrollmentObservations = 0
            current = HostMeshStatus(HostMeshStatus.State.ENROLLING)
        } catch (failure: Exception) {
            current = failureStatus(failure)
            throw failure
        }
    }

    override suspend fun stop() = operationLock.withLock {
        try {
            backend.stop()
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
            current = failureStatus(failure)
            return@withLock current
        }
        current = when (observed.state) {
            BackendMeshSnapshot.State.STOPPED -> HostMeshStatus(HostMeshStatus.State.STOPPED)
            BackendMeshSnapshot.State.ENROLLING -> {
                enrollmentObservations += 1
                if (enrollmentObservations > MAX_ENROLLMENT_OBSERVATIONS) {
                    HostMeshStatus(HostMeshStatus.State.ERROR, detail = "enrollment_not_completed")
                } else {
                    HostMeshStatus(HostMeshStatus.State.ENROLLING)
                }
            }
            BackendMeshSnapshot.State.ERROR -> HostMeshStatus(
                HostMeshStatus.State.ERROR,
                detail = observed.failure?.take(MAX_FAILURE_DETAIL_LENGTH) ?: "libtailscale_failure",
            )
            BackendMeshSnapshot.State.RUNNING -> {
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
            current = HostMeshStatus(HostMeshStatus.State.STOPPED)
        } catch (failure: Exception) {
            current = failureStatus(failure)
            throw failure
        }
    }

    private fun parseConfiguration(configuration: HostMeshConfiguration): PersistedMeshConfiguration {
        require(configuration.controlUrl.length <= MAX_CONTROL_URL_LENGTH) { "control URL is too long" }
        val uri = URI(configuration.controlUrl)
        require(uri.scheme == "https" || uri.scheme == "http") { "control URL must use HTTP(S)" }
        require(!uri.host.isNullOrBlank() && uri.userInfo == null && uri.query == null && uri.fragment == null) {
            "control URL must be an absolute server URL"
        }
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
        const val MAX_ENROLLMENT_OBSERVATIONS = 12
        val HOSTNAME = Regex("[a-z0-9][a-z0-9-]{0,62}")
    }
}
