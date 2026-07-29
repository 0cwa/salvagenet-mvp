package org.nodehost.api

import io.ktor.utils.io.ByteChannel
import io.ktor.utils.io.writeFully
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class BoundedBodyTest {
    @Test fun stalledReceiveChannelHitsOverallDeadline() = runTest {
        val failure = async {
            runCatching {
                readBoundedBody(
                    receive = { awaitCancellation() },
                    maximumBytes = 32,
                    idleTimeoutMillis = 50,
                    overallTimeoutMillis = 100,
                )
            }.exceptionOrNull()
        }
        advanceTimeBy(99)
        runCurrent()
        assertTrue(!failure.isCompleted)
        advanceTimeBy(1)
        runCurrent()

        assertTrue(failure.await() is HostApiRequestTimeoutException)
    }

    @Test fun neverSendingBodyHitsIdleDeadlineAndCancelsTransport() = runTest {
        val transport = ByteChannel(autoFlush = true)
        val failure = async {
            runCatching { readBoundedBody({ transport }, 32, idleTimeoutMillis = 100, overallTimeoutMillis = 1_000) }
                .exceptionOrNull()
        }
        advanceTimeBy(99)
        runCurrent()
        assertTrue(!failure.isCompleted)
        advanceTimeBy(1)
        runCurrent()

        assertTrue(failure.await() is HostApiRequestTimeoutException)
        assertEquals("request body timed out", failure.await()?.message)
        assertTrue(transport.isClosedForRead)
    }

    @Test fun slowDripCannotExtendOverallDeadline() = runTest {
        val transport = ByteChannel(autoFlush = true)
        val producer = launch {
            repeat(10) {
                transport.writeFully(byteArrayOf(it.toByte()))
                delay(60)
            }
            transport.close()
        }

        val failure = async {
            runCatching { readBoundedBody({ transport }, 32, idleTimeoutMillis = 100, overallTimeoutMillis = 250) }
                .exceptionOrNull()
        }
        advanceTimeBy(249)
        runCurrent()
        assertTrue(!failure.isCompleted)
        advanceTimeBy(1)
        runCurrent()

        assertTrue(failure.await() is HostApiRequestTimeoutException)
        assertTrue(transport.isClosedForRead)
        producer.cancelAndJoin()
    }

    @Test fun bodyOverMaximumCancelsTransport() = runTest {
        val transport = ByteChannel(autoFlush = true)
        val producer = launch { transport.writeFully(ByteArray(9) { 1 }) }

        val failure = async {
            runCatching { readBoundedBody({ transport }, 8, idleTimeoutMillis = 100, overallTimeoutMillis = 1_000) }
                .exceptionOrNull()
        }

        assertTrue(failure.await() is IllegalArgumentException)
        assertTrue(transport.isClosedForRead)
        producer.cancelAndJoin()
    }

    @Test fun normalChunkedBodyIsReturnedExactly() = runTest {
        val transport = ByteChannel(autoFlush = true)
        launch {
            transport.writeFully("normal".toByteArray())
            delay(20)
            transport.writeFully("-body".toByteArray())
            transport.close()
        }

        val body = readBoundedBody({ transport }, 32, idleTimeoutMillis = 100, overallTimeoutMillis = 500)

        assertArrayEquals("normal-body".toByteArray(), body)
    }

    @Test fun callerCancellationCancelsTransportPromptly() = runTest {
        val transport = ByteChannel(autoFlush = true)
        val reader = launch {
            readBoundedBody({ transport }, 32, idleTimeoutMillis = 1_000, overallTimeoutMillis = 2_000)
        }
        runCurrent()

        reader.cancelAndJoin()

        assertTrue(transport.isClosedForRead)
    }
}
