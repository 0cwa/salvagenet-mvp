# ADR-008-durable-operations — Room-backed current state and operation journal

Status: Accepted for MVP scaffold

## Decision

Use direct current state plus journaled stable steps, not event sourcing.

## Consequences

Implementation must satisfy the relevant module dependency rules and acceptance ledger. Reversal requires an ADR update plus migration/test plan.
