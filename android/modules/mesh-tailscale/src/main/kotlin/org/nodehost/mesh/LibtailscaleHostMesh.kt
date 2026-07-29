package org.nodehost.mesh

import org.nodehost.core.*

/**
 * Compile-safe scaffold. T05 replaces internals with pinned official Android-aware libtailscale.
 * No generic desktop tsnet assumptions belong here.
 */
class LibtailscaleHostMesh : HostMesh {
    private var current = HostMeshStatus(HostMeshStatus.State.STOPPED)
    override suspend fun configure(configuration: HostMeshConfiguration) {
        require(configuration.controlUrl.startsWith("https://") || configuration.controlUrl.startsWith("http://"))
        current = HostMeshStatus(HostMeshStatus.State.NEEDS_PERMISSION)
        // TODO(MVP-HARDENING, T05): pass configuration through LocalAPI/policy and erase the auth key after confirmed login.
    }
    override suspend fun start() { current = HostMeshStatus(HostMeshStatus.State.ENROLLING) }
    override suspend fun stop() { current = HostMeshStatus(HostMeshStatus.State.STOPPED) }
    override suspend fun status(): HostMeshStatus = current
    override suspend fun clearIdentity() { current = HostMeshStatus(HostMeshStatus.State.STOPPED) }
}
