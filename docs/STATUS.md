# MVP status

> Generated from `docs/roadmap/acceptance-ledger.md` by `tools/status/generate.py`. Do not edit by hand.

## Current verdict

**Device-lab candidate — not yet a validated MVP.**

10 of 20 base gates pass. The remaining 10 gates require physical-device or live-network evidence.

| Base status | Count |
|---|---:|
| `BLOCKED-HARDWARE` | 10 |
| `PASS` | 10 |

## Remaining base gates

| ID | Criterion | Status | Evidence |
|---|---|---|---|
| B02 | Known-good Podroid QEMU guest boots on physical ARM64 Android | `BLOCKED-HARDWARE` | [record](../evidence/gates/B02.json) |
| B07 | Desired state and operations survive Activity/service recreation | `BLOCKED-HARDWARE` | [record](../evidence/gates/B07.json) |
| B08 | Embedded host Tailscale joins Headscale | `BLOCKED-HARDWARE` | [record](../evidence/gates/B08.json) |
| B09 | Typed Host API reachable through host mesh and authenticated | `BLOCKED-HARDWARE` | [record](../evidence/gates/B09.json) |
| B10 | Controller remotely applies/imports one VM generation | `BLOCKED-HARDWARE` | [record](../evidence/gates/B10.json) |
| B11 | Guest receives key-only SSH and separate Headscale identity | `BLOCKED-HARDWARE` | [record](../evidence/gates/B11.json) |
| B12 | Ordinary SSH reaches guest through guest mesh | `BLOCKED-HARDWARE` | [record](../evidence/gates/B12.json) |
| B13 | Recovery SSH works with guest mesh disabled | `BLOCKED-HARDWARE` | [record](../evidence/gates/B13.json) |
| B16 | Reboot reconciles after first unlock | `BLOCKED-HARDWARE` | [record](../evidence/gates/B16.json) |
| B17 | Controller offline does not stop VM | `BLOCKED-HARDWARE` | [record](../evidence/gates/B17.json) |

## Passed software/base gates

| ID | Criterion | Evidence |
|---|---|---|
| B01 | Pinned Podroid baseline imported and builds | [record](../evidence/gates/B01.json) |
| B03 | Typed QEMU compiler preserves baseline invariants and snapshots | [record](../evidence/gates/B03.json) |
| B04 | Alpine direct and Ubuntu UEFI profiles resolve through same backend | [record](../evidence/gates/B04.json) |
| B05 | K3s lab profile emits qualification report | [record](../evidence/gates/B05.json) |
| B06 | Enrollment JSON validates and imports without executable fields | [record](../evidence/gates/B06.json) |
| B14 | Graceful stop precedes force kill | [record](../evidence/gates/B14.json) |
| B15 | System reset preserves designated data disk | [record](../evidence/gates/B15.json) |
| B18 | No default password, raw shell, raw QMP, or raw argv API | [record](../evidence/gates/B18.json) |
| B19 | Native artifacts pass required alignment/install checks | [record](../evidence/gates/B19.json) |
| B20 | Diagnostics redact secrets | [record](../evidence/gates/B20.json) |

## MVP+

MVP+ remains blocked until every base gate is `PASS`.

| ID | Criterion | Status |
|---|---|---|
| U01 | Linux `node-linkd` establishes AOA control link | `DEFERRED` |
| U02 | QEMU guest receives `eth1` over USB stream | `DEFERRED` |
| U03 | Linux TAP/NAT provides guest internet | `DEFERRED` |
| U04 | Disconnect falls back to SLIRP | `DEFERRED` |

## Next validation order

1. **D01:** install the exact CI-built APK and close B02 with a real QMP-qualified Alpine boot.
2. **D02:** close B08–B09 with host Headscale enrollment and authenticated Host API reachability.
3. **D03:** close B10–B12 with Ubuntu deployment, cloud-init, guest Tailscale, and ordinary SSH.
4. **D04:** close B13 by disabling guest mesh and using the bounded host recovery proxy.
5. **D05:** close B07 and B16–B17 through Activity/service/process/reboot/offline-controller tests.
6. **D07:** bind all evidence to one source commit and exact APK before calling the result the MVP.
