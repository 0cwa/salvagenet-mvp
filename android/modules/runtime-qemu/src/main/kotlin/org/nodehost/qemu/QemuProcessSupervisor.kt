package org.nodehost.qemu

import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.withTimeout

/** Public lifecycle surface. Command compilation and the QMP socket remain module-internal. */
class QemuRuntimeAdapter {
    private val supervisor = QemuProcessSupervisor()

    suspend fun start(plan: QemuLaunchPlan): QemuProcessHandle = supervisor.start(QemuCommandCompiler().compile(plan.resolved))
    suspend fun awaitExit(handle: QemuProcessHandle): QemuExit = handle.exit.await()
    suspend fun awaitQmpReady(handle: QemuProcessHandle): String =
        QmpSession(handle.qmpSocketPath).use { qmp ->
            qmp.connect()
            qmp.queryStatus()
        }
    suspend fun requestGuestShutdown(handle: QemuProcessHandle) {
        QmpSession(handle.qmpSocketPath).use { qmp -> qmp.connect(); qmp.systemPowerdown() }
    }
    fun requestStop() = supervisor.terminate()
    fun forceStop() = supervisor.forceTerminate()
}

class QemuProcessHandle internal constructor(
    val processId: Long?,
    internal val exit: Deferred<QemuExit>,
    internal val qmpSocketPath: File,
)
data class QemuExit(val code: Int, val stderrTail: List<String>)

/** Keeps launcher spawn and wait/reap in one long-lived runnable, as required by PR_SET_PDEATHSIG. */
internal class QemuProcessSupervisor(
    private val processFactory: ProcessFactory = JvmProcessFactory,
) {
    private val lock = Any()
    private var active: Lifetime? = null

    suspend fun start(descriptor: QemuLaunchDescriptor): QemuProcessHandle {
        val lifetime = synchronized(lock) {
            check(active == null) { "QEMU already running" }
            prepare(descriptor)
            Lifetime(newExecutor()).also { active = it }
        }
        lifetime.executor.execute { runLifetime(lifetime, descriptor) }
        return try {
            val process = withTimeout(START_TIMEOUT_MS) { lifetime.started.await() }
            QemuProcessHandle(
                processId(process), lifetime.exited,
                descriptor.sockets.single { it.name == "qmp.sock" },
            )
        } catch (failure: Throwable) {
            lifetime.cancelled = true
            lifetime.process?.destroyForcibly()
            throw failure
        }
    }

    fun terminate() { synchronized(lock) { active?.process }?.destroy() }
    fun forceTerminate() { synchronized(lock) { active?.process }?.destroyForcibly() }

    private fun runLifetime(lifetime: Lifetime, descriptor: QemuLaunchDescriptor) {
        var stderrThread: Thread? = null
        try {
            val process = processFactory.start(descriptor)
            lifetime.process = process
            if (lifetime.cancelled) process.destroyForcibly()
            stderrThread = Thread({ drainStderr(process, lifetime.stderrTail) }, "nodehost-qemu-stderr").apply {
                isDaemon = true
                start()
            }
            lifetime.started.complete(process)
            val code = process.waitFor()
            stderrThread.join(STDERR_JOIN_TIMEOUT_MS)
            lifetime.exited.complete(QemuExit(code, synchronized(lifetime.stderrTail) { lifetime.stderrTail.toList() }))
        } catch (failure: Throwable) {
            lifetime.started.completeExceptionally(failure)
            lifetime.exited.completeExceptionally(failure)
        } finally {
            lifetime.process = null
            descriptor.sockets.forEach { it.delete() }
            synchronized(lock) { if (active === lifetime) active = null }
            lifetime.executor.shutdown()
        }
    }

    private fun prepare(descriptor: QemuLaunchDescriptor) {
        require(descriptor.executable.isFile) { "QEMU executable is missing" }
        require(descriptor.workingDirectory.mkdirs() || descriptor.workingDirectory.isDirectory) { "cannot create instance directory" }
        descriptor.sockets.forEach { socket ->
            if (socket.exists() && !socket.delete()) error("cannot remove stale socket ${socket.name}")
        }
    }

    private fun drainStderr(process: Process, tail: MutableList<String>) {
        process.errorStream.bufferedReader().use { reader ->
            val line = StringBuilder()
            while (true) {
                val value = reader.read()
                if (value < 0) {
                    recordStderrLine(line, tail)
                    return
                }
                if (value.toChar() == '\n') {
                    recordStderrLine(line, tail)
                    line.setLength(0)
                } else if (line.length < MAX_STDERR_LINE_CHARS) {
                    line.append(value.toChar())
                }
            }
        }
    }

    private fun recordStderrLine(line: StringBuilder, tail: MutableList<String>) {
        val text = line.toString().trimEnd('\r')
        if (text.isBlank()) return
        synchronized(tail) {
            tail += text
            if (tail.size > MAX_STDERR_LINES) tail.removeAt(0)
        }
    }

    private fun processId(process: Process): Long? = runCatching {
        (Process::class.java.getMethod("pid").invoke(process) as Number).toLong()
    }.getOrNull()

    private fun newExecutor(): ExecutorService = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "nodehost-qemu-spawn-reap").apply { isDaemon = true }
    }

    private class Lifetime(val executor: ExecutorService) {
        val started = CompletableDeferred<Process>()
        val exited = CompletableDeferred<QemuExit>()
        val stderrTail = mutableListOf<String>()
        @Volatile var process: Process? = null
        @Volatile var cancelled = false
    }

    internal fun interface ProcessFactory { fun start(descriptor: QemuLaunchDescriptor): Process }

    private object JvmProcessFactory : ProcessFactory {
        override fun start(descriptor: QemuLaunchDescriptor): Process {
            val launcher = descriptor.launcher?.takeIf(File::isFile)
            val argv = listOfNotNull(launcher?.path, descriptor.executable.path) + descriptor.arguments
            return ProcessBuilder(argv)
                .directory(descriptor.workingDirectory)
                .redirectOutput(File("/dev/null"))
                .apply { environment().putAll(descriptor.environment) }
                .start()
        }
    }

    private companion object {
        const val START_TIMEOUT_MS = 10_000L
        const val STDERR_JOIN_TIMEOUT_MS = 1_000L
        const val MAX_STDERR_LINES = 40
        const val MAX_STDERR_LINE_CHARS = 1_024
    }
}
