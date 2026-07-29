# ADR-004-podroid-qemu-contract — Preserve Podroid APK-native QEMU launch contract

Status: Accepted for MVP scaffold

## Decision

Retain nativeLibraryDir executable packaging, launcher, dedicated spawn/reap thread, Unix sockets, diagnostics, and 16 KiB knowledge while wrapping them in a typed adapter.

## Consequences

Implementation must satisfy the relevant module dependency rules and acceptance ledger. Reversal requires an ADR update plus migration/test plan.
