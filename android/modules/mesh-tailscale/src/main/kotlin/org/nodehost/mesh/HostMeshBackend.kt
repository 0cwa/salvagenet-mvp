package org.nodehost.mesh

import org.nodehost.core.HostMeshConfiguration

internal data class BackendMeshSnapshot(
    val state: State,
    val addresses: List<String> = emptyList(),
    val failure: String? = null,
) {
    enum class State { STOPPED, ENROLLING, RUNNING, ERROR }
}

/** Narrow seam around the generated official libtailscale binding. */
internal interface HostMeshBackend {
    suspend fun configure(configuration: HostMeshConfiguration)
    suspend fun start(oneUseAuthKey: String?)
    suspend fun stop()
    suspend fun snapshot(): BackendMeshSnapshot
    suspend fun logout()
}

internal data class PersistedMeshConfiguration(
    val controlUrl: String,
    val hostname: String,
    val oneUseAuthKey: String?,
)

internal interface MeshConfigurationStore {
    suspend fun save(configuration: PersistedMeshConfiguration)
    suspend fun load(): PersistedMeshConfiguration?
    suspend fun deleteOneUseAuthKey()
    suspend fun clear()
}
