# node-core instructions

- Depends only on `node-model` and standard/Kotlin concurrency primitives.
- Use cases change desired state or create operations; adapters perform effects.
- One reconciliation actor mutates runtime state.
- Stable step IDs must survive process death and retries.
- Do not import platform or adapter types.
