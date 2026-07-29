# control-api instructions

- `control/openapi.yaml` is authoritative.
- Handlers call node-core use cases; no direct QEMU/Room/Tailscale access.
- Never add shell, raw QMP, raw argv, or unrestricted forwarding endpoints.
- Keep Ktor and MVP capability authentication behind interfaces.
- Authorization headers and credentials are always redacted.
