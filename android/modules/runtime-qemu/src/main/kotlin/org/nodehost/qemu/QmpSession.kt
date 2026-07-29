package org.nodehost.qemu

interface QmpSession {
    suspend fun connect()
    suspend fun queryStatus(): String
    suspend fun systemPowerdown()
    suspend fun quit()
    suspend fun close()
}

// TODO(MVP-HARDENING, T02): replace the first minimal implementation with a persistent
// request-ID/event-correlating actor. Keep this interface stable for the reconciler.
