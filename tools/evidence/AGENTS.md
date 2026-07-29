# Evidence tooling instructions

- Generate compact, deterministic, redacted gate records only.
- Never read or serialize live auth-key/credential files.
- Git trailers, not evidence JSON, carry agent/model provenance.
- A `PASS` record must name a reproducible command; the tool must not mark the
  acceptance ledger automatically.
