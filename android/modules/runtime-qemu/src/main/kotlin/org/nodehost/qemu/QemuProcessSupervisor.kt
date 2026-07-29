package org.nodehost.qemu

import java.io.File
import java.util.concurrent.Executors
import kotlinx.coroutines.*

/** Preserves Podroid's dedicated spawn/reap-thread constraint. */
class QemuProcessSupervisor {
    private var dispatcher: ExecutorCoroutineDispatcher? = null
    @Volatile private var process: Process? = null

    suspend fun start(descriptor: QemuLaunchDescriptor): Process = withContext(Dispatchers.IO) {
        check(process?.isAlive != true) { "QEMU already running" }
        val dedicated = Executors.newSingleThreadExecutor { runnable -> Thread(runnable, "nodehost-qemu").apply { isDaemon = true } }.asCoroutineDispatcher()
        dispatcher = dedicated
        val builder = ProcessBuilder(descriptor.argv()).directory(File(descriptor.workingDirectory))
        builder.environment().putAll(descriptor.environment)
        builder.redirectOutput(File("/dev/null"))
        withContext(dedicated) { builder.start() }.also { process = it }
    }

    suspend fun awaitExit(): Int {
        val proc = requireNotNull(process)
        val owner = requireNotNull(dispatcher)
        return withContext(owner) { proc.waitFor() }.also { process = null; owner.close(); dispatcher = null }
    }

    fun terminate() { process?.destroy() }
    fun forceTerminate() { process?.destroyForcibly() }
}
