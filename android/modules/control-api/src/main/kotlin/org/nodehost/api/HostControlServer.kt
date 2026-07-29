package org.nodehost.api

import io.ktor.http.ContentType
import io.ktor.http.HttpMethod
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.ApplicationCall
import io.ktor.server.application.call
import io.ktor.server.application.install
import io.ktor.server.cio.CIO
import io.ktor.server.engine.EmbeddedServer
import io.ktor.server.engine.embeddedServer
import io.ktor.server.engine.sslConnector
import io.ktor.server.plugins.statuspages.StatusPages
import io.ktor.server.plugins.statuspages.exception
import io.ktor.server.request.header
import io.ktor.server.request.httpMethod
import io.ktor.server.request.path
import io.ktor.server.request.receiveChannel
import io.ktor.server.response.respondBytesWriter
import io.ktor.server.response.respondText
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.method
import io.ktor.server.routing.post
import io.ktor.server.routing.put
import io.ktor.server.routing.route
import io.ktor.server.routing.routing
import io.ktor.utils.io.readAvailable
import io.ktor.utils.io.writeFully
import java.net.InetAddress
import java.security.KeyStore
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import org.nodehost.core.ControllerPrincipal

class TlsServerCredentials(
    val keyStore: KeyStore,
    val keyAlias: String,
    internal val keyStorePassword: CharArray,
    internal val privateKeyPassword: CharArray,
) {
    init { require(keyAlias.isNotBlank()) { "TLS key alias is required" } }
    override fun toString(): String = "TlsServerCredentials(keyAlias=$keyAlias, passwords=[REDACTED])"
}

/** Ktor TLS transport adapter; server and credential provisioning remain replaceable ports. */
class HostControlServer(
    private val controller: HostApiController,
    private val tls: TlsServerCredentials,
) : HostApiServer {
    private var server: EmbeddedServer<*, *>? = null

    @Synchronized
    override fun start(bindAddress: String, port: Int) {
        requireSafeBindAddress(bindAddress)
        require(port in 1..65535) { "invalid API port" }
        check(server == null) { "Host API already started" }
        server = embeddedServer(CIO, configure = {
            sslConnector(
                keyStore = tls.keyStore,
                keyAlias = tls.keyAlias,
                keyStorePassword = { tls.keyStorePassword.copyOf() },
                privateKeyPassword = { tls.privateKeyPassword.copyOf() },
            ) {
                host = bindAddress
                this.port = port
            }
        }) {
            install(StatusPages) {
                exception<HostApiConflictException> { call, cause ->
                    call.problem(HttpStatusCode.Conflict, "CONFLICT", cause.message ?: "mutation conflict")
                }
                exception<IllegalArgumentException> { call, cause ->
                    call.problem(HttpStatusCode.BadRequest, "INVALID_REQUEST", cause.message ?: "invalid request")
                }
                exception<Throwable> { call, _ ->
                    // Deliberately omit exception detail: it can contain adapter or credential data.
                    call.problem(HttpStatusCode.InternalServerError, "INTERNAL_ERROR", "request failed")
                }
            }
            routing {
                get("/v1/status") { authenticated { call.json(controller.status()) } }
                get("/v1/capabilities") { authenticated { call.json(controller.capabilities()) } }
                get("/v1/profiles") { authenticated { call.json(controller.profiles()) } }
                get("/v1/images") { authenticated { call.json(controller.images()) } }
                post("/v1/image-imports") {
                    authenticated {
                        val raw = call.boundedBody()
                        val (request, canonical) = HostApiJson.parseImageImport(raw)
                        call.json(
                            HostApiJson.operation(controller.importImage(request, call.idempotencyKey(), canonical)),
                            HttpStatusCode.Accepted,
                        )
                    }
                }
                get("/v1/vms") { authenticated { call.json(controller.vms()) } }
                get("/v1/vms/{id}") {
                    authenticated {
                        val value = controller.vm(call.pathParameter("id"))
                        if (value == null) call.problem(HttpStatusCode.NotFound, "NOT_FOUND", "VM not found")
                        else call.json(value)
                    }
                }
                put("/v1/vms/{id}") {
                    authenticated {
                        val id = call.pathParameter("id")
                        val (request, canonical) = HostApiJson.parseApplyVm(id, call.boundedBody())
                        call.json(
                            HostApiJson.operation(controller.applyVm(request, call.idempotencyKey(), canonical)),
                            HttpStatusCode.Accepted,
                        )
                    }
                }
                delete("/v1/vms/{id}") {
                    authenticated {
                        val id = call.pathParameter("id")
                        val canonical = "remove:$id".toByteArray()
                        call.json(
                            HostApiJson.operation(controller.removeVm(id, call.idempotencyKey(), canonical)),
                            HttpStatusCode.Accepted,
                        )
                    }
                }
                get("/v1/operations") {
                    authenticated { call.json(controller.operations().map(HostApiJson::operation)) }
                }
                get("/v1/operations/{id}") {
                    authenticated {
                        val value = controller.operation(call.pathParameter("id"))
                        if (value == null) call.problem(HttpStatusCode.NotFound, "NOT_FOUND", "operation not found")
                        else call.json(HostApiJson.operation(value))
                    }
                }
                post("/v1/operations/{id}/cancel") {
                    authenticated {
                        val id = call.pathParameter("id")
                        val canonical = "cancel:$id".toByteArray()
                        call.json(
                            HostApiJson.operation(controller.cancelOperation(id, call.idempotencyKey(), canonical)),
                            HttpStatusCode.Accepted,
                        )
                    }
                }
                get("/v1/diagnostics") { authenticated { call.json(controller.diagnostics()) } }
                delete("/v1/controllers/{id}") {
                    authenticated {
                        val id = call.pathParameter("id")
                        controller.revokeController(id, call.idempotencyKey(), "revoke:$id".toByteArray())
                        call.respondText("", status = HttpStatusCode.NoContent)
                    }
                }
                route("/v1/vms/{id}/ssh") {
                    method(HttpMethod("CONNECT")) {
                        handle {
                            authenticatedPrincipal { principal ->
                                val session = controller.openRecovery(call.pathParameter("id"), principal)
                                call.respondBytesWriter(ContentType.Application.OctetStream, HttpStatusCode.OK) {
                                    coroutineScope {
                                        val requestBytes = call.receiveChannel()
                                        val inbound = launch {
                                            val buffer = ByteArray(64 * 1024)
                                            while (true) {
                                                val count = requestBytes.readAvailable(buffer)
                                                if (count == -1) break
                                                if (count > 0) session.write(buffer.copyOf(count))
                                            }
                                        }
                                        try {
                                            while (true) {
                                                val bytes = session.read(64 * 1024) ?: break
                                                require(bytes.isNotEmpty() && bytes.size <= 64 * 1024) {
                                                    "invalid recovery stream chunk"
                                                }
                                                writeFully(bytes)
                                                flush()
                                            }
                                        } finally {
                                            inbound.cancelAndJoin()
                                            session.close()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }.start(wait = false)
    }

    @Synchronized
    override fun stop() {
        server?.stop(gracePeriodMillis = 500, timeoutMillis = 2_000)
        server = null
    }

    private suspend fun io.ktor.server.routing.RoutingContext.authenticatedPrincipal(
        block: suspend (ControllerPrincipal) -> Unit,
    ) {
        val principal = controller.authorize(
            call.request.header("Authorization"),
            call.request.httpMethod.value,
            call.request.path(),
        )
        if (principal == null) call.problem(HttpStatusCode.Unauthorized, "UNAUTHORIZED", "authentication required")
        else block(principal)
    }

    private suspend fun io.ktor.server.routing.RoutingContext.authenticated(block: suspend () -> Unit) =
        authenticatedPrincipal { block() }

    companion object {
        fun requireSafeBindAddress(value: String) {
            val address = runCatching { InetAddress.getByName(value) }.getOrElse {
                throw IllegalArgumentException("bind address must be a literal loopback or tailnet address")
            }
            require(value == address.hostAddress || value.removePrefix("[").removeSuffix("]") == address.hostAddress) {
                "bind address must be a literal loopback or tailnet address"
            }
            val bytes = address.address
            val tailscaleV4 = bytes.size == 4 && (bytes[0].toInt() and 0xff) == 100 &&
                ((bytes[1].toInt() and 0xff) in 64..127)
            val tailscaleV6 = bytes.size == 16 && bytes[0] == 0xfd.toByte() && bytes[1] == 0x7a.toByte() &&
                bytes[2] == 0x11.toByte() && bytes[3] == 0x5c.toByte() && bytes[4] == 0xa1.toByte() &&
                bytes[5] == 0xe0.toByte()
            require(address.isLoopbackAddress || tailscaleV4 || tailscaleV6) {
                "Host API may bind only loopback or Tailscale address space"
            }
        }
    }
}

private suspend fun ApplicationCall.boundedBody(): ByteArray {
    val declared = request.header("Content-Length")?.toLongOrNull()
    require(declared == null || declared in 0..HostApiController.MAX_REQUEST_BYTES.toLong()) {
        "request body is too large"
    }
    val channel = receiveChannel()
    val output = java.io.ByteArrayOutputStream()
    val buffer = ByteArray(8192)
    while (true) {
        val count = channel.readAvailable(buffer)
        if (count == -1) break
        if (count == 0) continue
        require(output.size() + count <= HostApiController.MAX_REQUEST_BYTES) { "request body is too large" }
        output.write(buffer, 0, count)
    }
    return output.toByteArray()
}

private fun ApplicationCall.pathParameter(name: String): String =
    parameters[name] ?: throw IllegalArgumentException("missing $name")

private fun ApplicationCall.idempotencyKey(): String =
    request.header("Idempotency-Key") ?: throw IllegalArgumentException("Idempotency-Key is required")

private suspend fun ApplicationCall.json(value: Any?, status: HttpStatusCode = HttpStatusCode.OK) {
    respondText(HostApiJson.encode(value), ContentType.Application.Json, status)
}

private suspend fun ApplicationCall.problem(status: HttpStatusCode, code: String, detail: String) {
    val value = mapOf(
        "type" to "https://nodehost.invalid/problems/${code.lowercase()}",
        "title" to status.description,
        "status" to status.value,
        "detail" to detail.take(512),
        "code" to code,
    )
    respondText(HostApiJson.encode(value), ContentType.Application.ProblemJson, status)
}
