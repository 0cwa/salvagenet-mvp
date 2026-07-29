package org.nodehost.qemu

import java.io.File
import java.util.ArrayDeque
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class QmpSessionTest {
    @Test
    fun exposesOnlyFixedCommandsAndCorrelatesBoundedResponses() = runBlocking {
        val transport = FakeTransport(
            "{\"QMP\":{\"version\":{}}}",
            "{\"return\":{},\"id\":1}",
            "{\"event\":\"STOP\"}",
            "{\"return\":{\"status\":\"running\"},\"id\":2}",
            "{\"return\":{},\"id\":3}",
        )
        val session = QmpSession(File("/private/vms/default/qmp.sock")) { transport }
        session.connect()
        assertEquals("running", session.queryStatus())
        session.systemPowerdown()
        session.close()

        assertEquals(listOf("qmp_capabilities", "query-status", "system_powerdown"), transport.writes.map { COMMAND.find(it)!!.groupValues[1] })
        assertTrue(transport.closed)
    }

    @Test
    fun reportsQmpErrorsInsteadOfSwallowingThem() {
        val failure = assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                val transport = FakeTransport(
                    "{\"QMP\":{}}", "{\"return\":{},\"id\":1}",
                    "{\"error\":{\"class\":\"GenericError\"},\"id\":2}",
                )
                QmpSession(File("/private/qmp.sock")) { transport }.apply { connect(); queryStatus() }
            }
        }
        assertTrue(failure.message!!.contains("failed"))
    }

    private class FakeTransport(vararg responses: String) : QmpTransport {
        private val responses = ArrayDeque(responses.toList())
        val writes = mutableListOf<String>()
        var closed = false
        override suspend fun connect(path: File) = Unit
        override suspend fun writeLine(line: String) { writes += line }
        override suspend fun readLineBounded(): String = responses.removeFirst()
        override fun close() { closed = true }
    }

    private companion object { val COMMAND = Regex("\\\"execute\\\":\\\"([^\\\"]+)\\\"") }
}
