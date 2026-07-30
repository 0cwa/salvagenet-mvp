# MVP CLI instructions

- Python standard library first.
- Read endpoint/capability from an ignored config or environment.
- Redact authorization values, upload idempotency keys, and secrets in all output/errors.
- Poll durable operations; do not invent local desired state.
- ProxyCommand forwards bytes only to the bounded VM recovery endpoint.
- Keep API paths synchronized with OpenAPI tests.
- Artifact upload streams the local file in bounded chunks; never buffer a VM image into memory.
- Verify the local file's exact size and SHA-256 before creating or resuming an upload.
- Derive deterministic create idempotency from artifact ID, digest, and size, then trust only the host-reported committed offset for resume.
- Retry only exact replay or connection failure boundaries. Surface `404` missing-resource and `409` upload/idempotency conflicts rather than silently creating divergent state.
- Completion succeeds only after the host returns the published image identity matching the requested artifact ID, digest, and size.
