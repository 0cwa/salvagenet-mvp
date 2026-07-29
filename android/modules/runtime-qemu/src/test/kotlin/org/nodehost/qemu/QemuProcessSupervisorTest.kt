package org.nodehost.qemu

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.InputStream
import java.io.OutputStream
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.io.path.createTempDirectory
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class QemuProcessSupervisorTest {
    @Test
    fun spawnAndReapUseSameDedicatedThreadAndCaptureBoundedDiagnostics() = runBlocking {
        val root = createTempDirectory("qemu-supervisor-").toFile()
        try {
            val executable = File(root, "qemu").apply { writeText("fixture") }
            val process = ControlledProcess((1..45).joinToString("\n") { "stderr-$it" })
            val supervisor = QemuProcessSupervisor { descriptor ->
                process.spawnThread = Thread.currentThread().name
                assertEquals(executable, descriptor.executable)
                process
            }
            val handle = supervisor.start(QemuTestFixtures.descriptor(root, executable))
            assertThrows(IllegalStateException::class.java) {
                runBlocking { supervisor.start(QemuTestFixtures.descriptor(root, executable)) }
            }
            process.finish(7)
            val exit = handle.exit.await()

            assertEquals(process.spawnThread, process.reapThread)
            assertTrue(process.spawnThread!!.contains("spawn-reap"))
            assertEquals(7, exit.code)
            assertEquals(40, exit.stderrTail.size)
            assertEquals("stderr-6", exit.stderrTail.first())
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun removesStaleSocketsBeforeStarting() = runBlocking {
        val root = createTempDirectory("qemu-stale-").toFile()
        try {
            val executable = File(root, "qemu").apply { writeText("fixture") }
            val descriptor = QemuTestFixtures.descriptor(root, executable)
            descriptor.workingDirectory.mkdirs()
            descriptor.sockets.single().writeText("stale")
            val process = ControlledProcess("")
            val supervisor = QemuProcessSupervisor { process }
            val handle = supervisor.start(descriptor)
            assertTrue(!descriptor.sockets.single().exists())
            process.finish(0)
            assertEquals(0, handle.exit.await().code)
        } finally {
            root.deleteRecursively()
        }
    }

    private class ControlledProcess(stderr: String) : Process() {
        private val done = CountDownLatch(1)
        private val stderr = ByteArrayInputStream(stderr.toByteArray())
        @Volatile private var code = 0
        @Volatile var spawnThread: String? = null
        @Volatile var reapThread: String? = null
        fun finish(code: Int) { this.code = code; done.countDown() }
        override fun waitFor(): Int { reapThread = Thread.currentThread().name; done.await(); return code }
        override fun waitFor(timeout: Long, unit: TimeUnit): Boolean = done.await(timeout, unit)
        override fun exitValue(): Int { check(done.count == 0L); return code }
        override fun destroy() = finish(143)
        override fun destroyForcibly(): Process { finish(137); return this }
        override fun isAlive(): Boolean = done.count != 0L
        override fun getInputStream(): InputStream = ByteArrayInputStream(byteArrayOf())
        override fun getErrorStream(): InputStream = stderr
        override fun getOutputStream(): OutputStream = ByteArrayOutputStream()
    }
}
