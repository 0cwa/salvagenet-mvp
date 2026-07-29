# control-api

Bounded typed Host API application/transport adapters. `HostApiController`
authenticates before delegating reads and mutations; VM apply uses node-core's
`ApplyRuntimeUseCase` so generation and idempotency remain atomically owned by
node-core. Ktor, MVP bearer authentication, image import, and recovery byte
streams are replaceable ports.

The CIO adapter requires TLS key material and may bind only a literal loopback
or Tailscale address. The composition root supplies credentials and durable port
implementations.
