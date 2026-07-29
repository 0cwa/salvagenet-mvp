package org.nodehost.model

data class CapabilityFact(val id: String, val supported: Boolean, val detail: String? = null) {
    init {
        require(Regex("[a-z][a-z0-9.-]{0,63}").matches(id))
        require(detail == null || detail.length <= 256)
    }
}

data class CapabilitySnapshot(val capturedAtEpochMs: Long, val facts: List<CapabilityFact>) {
    init {
        require(capturedAtEpochMs >= 0)
        require(facts.size <= 128)
        require(facts.map { it.id }.distinct().size == facts.size)
    }
}
