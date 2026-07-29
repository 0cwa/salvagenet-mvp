# ADR-009-mvp-security-adapter — Replaceable controller capability for MVP

Status: Accepted for MVP scaffold

## Decision

Use a high-entropy imported capability plus pinned HTTPS/tailnet restriction only as a named MVP adapter; preserve an authentication port for mTLS later.

## Consequences

Implementation must satisfy the relevant module dependency rules and acceptance ledger. Reversal requires an ADR update plus migration/test plan.
