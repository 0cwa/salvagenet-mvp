# ADR-001-product-boundary — Host substrate, not orchestrator

Status: Accepted for MVP scaffold

## Decision

The APK owns node identity, runtime lifecycle, recovery, and capability reporting. Workload/orchestrator state remains in upstream tools.

## Consequences

Implementation must satisfy the relevant module dependency rules and acceptance ledger. Reversal requires an ADR update plus migration/test plan.
