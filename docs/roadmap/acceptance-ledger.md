# Acceptance ledger

Status values: `TODO`, `IN-PROGRESS`, `PASS`, `FAIL`, `BLOCKED-HARDWARE`, `DEFERRED`.

<!-- BASE-MVP-BEGIN -->
| ID | Base criterion | Status | Evidence |
|---|---|---|---|
| B01 | Pinned Podroid baseline imported and builds | PASS | [record](../../evidence/gates/B01.json) |
| B02 | Known-good Podroid QEMU guest boots on physical ARM64 Android | BLOCKED-HARDWARE | [record](../../evidence/gates/B02.json) |
| B03 | Typed QEMU compiler preserves baseline invariants and snapshots | PASS | [record](../../evidence/gates/B03.json) |
| B04 | Alpine direct and Ubuntu UEFI profiles resolve through same backend | PASS | [record](../../evidence/gates/B04.json) |
| B05 | K3s lab profile emits qualification report | PASS | [record](../../evidence/gates/B05.json) |
| B06 | Enrollment JSON validates and imports without executable fields | PASS | [record](../../evidence/gates/B06.json) |
| B07 | Desired state and operations survive Activity/service recreation | BLOCKED-HARDWARE | [record](../../evidence/gates/B07.json) |
| B08 | Embedded host Tailscale joins Headscale | BLOCKED-HARDWARE | [record](../../evidence/gates/B08.json) |
| B09 | Typed Host API reachable through host mesh and authenticated | BLOCKED-HARDWARE | [record](../../evidence/gates/B09.json) |
| B10 | Controller remotely applies/imports one VM generation | BLOCKED-HARDWARE | [record](../../evidence/gates/B10.json) |
| B11 | Guest receives key-only SSH and separate Headscale identity | BLOCKED-HARDWARE | [record](../../evidence/gates/B11.json) |
| B12 | Ordinary SSH reaches guest through guest mesh | BLOCKED-HARDWARE | [record](../../evidence/gates/B12.json) |
| B13 | Recovery SSH works with guest mesh disabled | BLOCKED-HARDWARE | [record](../../evidence/gates/B13.json) |
| B14 | Graceful stop precedes force kill | PASS | [record](../../evidence/gates/B14.json) |
| B15 | System reset preserves designated data disk | PASS | [record](../../evidence/gates/B15.json) |
| B16 | Reboot reconciles after first unlock | BLOCKED-HARDWARE | [record](../../evidence/gates/B16.json) |
| B17 | Controller offline does not stop VM | BLOCKED-HARDWARE | [record](../../evidence/gates/B17.json) |
| B18 | No default password, raw shell, raw QMP, or raw argv API | PASS | [record](../../evidence/gates/B18.json) |
| B19 | Native artifacts pass required alignment/install checks | PASS | [record](../../evidence/gates/B19.json) |
| B20 | Diagnostics redact secrets | PASS | [record](../../evidence/gates/B20.json) |
<!-- BASE-MVP-END -->

<!-- MVP-PLUS-BEGIN -->
| ID | MVP+ criterion | Status | Evidence |
|---|---|---|---|
| U01 | Linux `node-linkd` establishes AOA control link | DEFERRED | [record](../../evidence/gates/U01.json) |
| U02 | QEMU guest receives `eth1` over USB stream | DEFERRED | [record](../../evidence/gates/U02.json) |
| U03 | Linux TAP/NAT provides guest internet | DEFERRED | [record](../../evidence/gates/U03.json) |
| U04 | Disconnect falls back to SLIRP | DEFERRED | [record](../../evidence/gates/U04.json) |
<!-- MVP-PLUS-END -->

Gate status changes require a reviewed evidence record that satisfies the criterion and evidence schema; no historical task owns status updates. Physical records should be promoted from the single HIL runner through the validated evidence tooling. The gate script requires every B-item to be PASS before executable changes under `usb-link/` are allowed.
