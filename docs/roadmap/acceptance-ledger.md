# Acceptance ledger

Status values: `TODO`, `IN-PROGRESS`, `PASS`, `FAIL`, `BLOCKED-HARDWARE`, `DEFERRED`.

<!-- BASE-MVP-BEGIN -->
| ID | Base criterion | Status | Evidence |
|---|---|---|---|
| B01 | Pinned Podroid baseline imported and builds | TODO | |
| B02 | Known-good Podroid QEMU guest boots on physical ARM64 Android | TODO | |
| B03 | Typed QEMU compiler preserves baseline invariants and snapshots | TODO | |
| B04 | Alpine direct and Ubuntu UEFI profiles resolve through same backend | TODO | |
| B05 | K3s lab profile emits qualification report | TODO | |
| B06 | Enrollment JSON validates and imports without executable fields | TODO | |
| B07 | Desired state and operations survive Activity/service recreation | TODO | |
| B08 | Embedded host Tailscale joins Headscale | TODO | |
| B09 | Typed Host API reachable through host mesh and authenticated | TODO | |
| B10 | Controller remotely applies/imports one VM generation | TODO | |
| B11 | Guest receives key-only SSH and separate Headscale identity | TODO | |
| B12 | Ordinary SSH reaches guest through guest mesh | TODO | |
| B13 | Recovery SSH works with guest mesh disabled | TODO | |
| B14 | Graceful stop precedes force kill | TODO | |
| B15 | System reset preserves designated data disk | TODO | |
| B16 | Reboot reconciles after first unlock | TODO | |
| B17 | Controller offline does not stop VM | TODO | |
| B18 | No default password, raw shell, raw QMP, or raw argv API | TODO | |
| B19 | Native artifacts pass required alignment/install checks | TODO | |
| B20 | Diagnostics redact secrets | TODO | |
<!-- BASE-MVP-END -->

<!-- MVP-PLUS-BEGIN -->
| ID | MVP+ criterion | Status | Evidence |
|---|---|---|---|
| U01 | Linux `node-linkd` establishes AOA control link | TODO | |
| U02 | QEMU guest receives `eth1` over USB stream | TODO | |
| U03 | Linux TAP/NAT provides guest internet | TODO | |
| U04 | Disconnect falls back to SLIRP | TODO | |
<!-- MVP-PLUS-END -->

Only T08/integration ownership updates base statuses. The gate script requires all B-items `PASS` before executable changes under `usb-link/` are allowed.
