# node-store implementation instructions

- Room entities, DAOs, and explicit migrations are the only product-schema authority.
- Do not create product tables from HTTP handlers, services, or runtime adapters.
- Desired-state, idempotency, operation-step, cancellation, and maintenance-slot changes are transactional and restart-safe.
- Never use destructive migration in product code.
- Bound journal/history growth and test reuse across process reconstruction.
- Persist secrets only through the designated encrypted/Keystore-backed seam; redact entity diagnostics and `toString` output.
- A migration change includes schema export, upgrade/downgrade policy, and focused recovery tests.
