package org.nodehost.api

import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.cio.CIO
import io.ktor.server.engine.EmbeddedServer
import io.ktor.server.engine.embeddedServer
import io.ktor.server.request.header
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import org.nodehost.core.ControllerAuthenticator

/**
 * Thin Ktor adapter used by the MVP. Route handlers authenticate and delegate
 * to node-core use cases; QEMU, Room, and Tailscale never enter this module.
 */
class HostControlServer(
    private val authenticator: ControllerAuthenticator,
) {
    private var server: EmbeddedServer<*, *>? = null

    fun start(host: String, port: Int) {
        check(server == null) { "Host API already started" }
        server = embeddedServer(CIO, host = host, port = port) {
            routing {
                get("/v1/status") {
                    val principal = authenticator.authorize(
                        authorization = call.request.header("Authorization"),
                        method = "GET",
                        path = "/v1/status",
                    )
                    if (principal == null) {
                        call.respondText(
                            text = """{"type":"about:blank","title":"Unauthorized","status":401}""",
                            contentType = ContentType.Application.ProblemJson,
                            status = HttpStatusCode.Unauthorized,
                        )
                    } else {
                        call.respondText(
                            text = """{"state":"scaffold","controller":"${principal.id}"}""",
                            contentType = ContentType.Application.Json,
                        )
                    }
                }
            }
        }.start(wait = false)
    }

    fun stop() {
        server?.stop(gracePeriodMillis = 500, timeoutMillis = 2_000)
        server = null
    }
}
