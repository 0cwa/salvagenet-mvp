# ADR-006-host-guest-mesh — Separate host and guest mesh identities

Status: Accepted for MVP scaffold

## Decision

Embedded Android Tailscale protects recovery and Host API; guest Tailscale carries ordinary SSH/workload traffic.

## Consequences

Implementation must satisfy the relevant module dependency rules and acceptance ledger. Reversal requires an ADR update plus migration/test plan.
