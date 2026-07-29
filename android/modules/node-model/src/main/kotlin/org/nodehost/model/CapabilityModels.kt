package org.nodehost.model

data class CapabilityFact(val id: String, val supported: Boolean, val detail: String? = null)
data class CapabilitySnapshot(val capturedAtEpochMs: Long, val facts: List<CapabilityFact>)
