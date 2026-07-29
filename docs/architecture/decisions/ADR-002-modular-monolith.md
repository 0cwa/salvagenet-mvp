# ADR-002-modular-monolith — Modular monolith with process adapters

Status: Accepted for MVP scaffold

## Decision

Use compile-time Android modules and one authoritative supervisor. QEMU is a child process; do not create in-phone microservices.

## Consequences

Implementation must satisfy the relevant module dependency rules and acceptance ledger. Reversal requires an ADR update plus migration/test plan.
