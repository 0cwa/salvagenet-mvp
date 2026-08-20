# control-api instructions

- `control/openapi.yaml` is authoritative.
- Handlers call node-core/use-case ports; no direct QEMU, Room, Tailscale, artifact-filesystem, or publication logic.
- Never add shell, raw QMP, raw argv, unrestricted forwarding, or arbitrary file-path endpoints.
- Keep Ktor and MVP capability authentication behind interfaces.
- Authorization headers, upload idempotency keys, and credentials are always redacted.
- Public HTTPS import and authenticated controller upload are separate resources. Never relax URL-origin, redirect, DNS-rebinding, digest, size, or deadline policy to support local delivery.
- Resumable upload chunks are sequential and bounded to 1 MiB. Exact replay may succeed; gaps, partial overlap, conflicting replay, terminal-state mutation, and idempotency reuse are typed conflicts.
- Missing upload resources return `404`; upload state/idempotency conflicts return `409`; malformed fields remain `400`.
- Keep route, JSON parser, OpenAPI, controller client, and tests synchronized whenever upload semantics change.
