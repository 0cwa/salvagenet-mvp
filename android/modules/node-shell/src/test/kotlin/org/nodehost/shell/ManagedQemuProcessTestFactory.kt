package org.nodehost.shell

import org.nodehost.qemu.QemuExit

/**
 * Test-only compatibility factory for fixtures that do not need to model QMP state transitions.
 * Production process handles still require an explicit QMP readiness callback.
 */
@Suppress("FunctionName")
internal fun ManagedQemuProcess(
    processId: Long?,
    awaitExit: suspend () -> QemuExit,
    requestGuestShutdown: suspend () -> Unit,
): ManagedQemuProcess = ManagedQemuProcess(
    processId = processId,
    awaitExit = awaitExit,
    awaitQmpReady = { "running" },
    requestGuestShutdown = requestGuestShutdown,
)
