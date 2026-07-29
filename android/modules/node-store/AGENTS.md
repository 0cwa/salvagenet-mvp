# node-store instructions

- Implements repository ports; no reconciliation policy.
- Export Room schema and use explicit migrations after schema version 1.
- Never use destructive migration in product code.
- Transactions bracket desired-state and operation-step updates.
- Redact secrets from entities' `toString` and diagnostics.
