# ADR-003-onion-and-reconciler — Onion dependencies and desired/observed reconciliation

Status: Accepted for MVP scaffold

## Decision

Domain/application modules are platform-free by imports. Side effects occur only through ports and durable operation steps.

## Consequences

Implementation must satisfy the relevant module dependency rules and acceptance ledger. Reversal requires an ADR update plus migration/test plan.
