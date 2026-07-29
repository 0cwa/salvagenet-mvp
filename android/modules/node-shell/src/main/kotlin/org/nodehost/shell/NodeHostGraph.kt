package org.nodehost.shell

import android.content.Context

object NodeHostGraph {
    @Volatile private var initialized = false
    @Synchronized fun initialize(context: Context) {
        if (initialized) return
        // TODO(MVP-HARDENING, T03): construct Room, reconciler, fake/real adapters, and encrypted secret storage.
        initialized = true
    }
}
