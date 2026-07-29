# node-model instructions

- Pure deterministic values and state transitions only.
- No Android, filesystem, network, QEMU, Tailscale, Room, Ktor, Podroid, or logging imports.
- Keep serialization DTOs in adapter modules or explicit contract mappers.
- Add table-driven unit tests for every state transition.
