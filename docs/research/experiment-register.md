# Experiment register

Append concise results here; do not paste full logs. `SOFTWARE-PASS/HARDWARE-OPEN` means the selected implementation and automated tests pass, but the research question still requires physical evidence.

| ID | Date | Source/evidence | Device/environment | Result | Decision impact |
|---|---|---|---|---|---|
| F00 | 2026-07-30 | `docs/research/experiments/F00.md`, PR #5, task/roadmap audit | Repository and GitHub CI | GOVERNANCE-PASS/CI-PENDING | Merge H01, archive completed tasks, queue H02/H03, activate only F01, and require phase-boundary acceptance review. |
| E01 | 2026-07-29 | `evidence/gates/B01.json`, `evidence/T08/qa-summary.txt` | Fedora build host | SOFTWARE-PASS | Podroid import, app build, and pinned runtime packaging are usable for device validation; project-owned native rebuild remains debt. |
| E02 | 2026-07-29 | `evidence/gates/B01.json`, Gradle module suites | Fedora build host | PASS | Keep sibling modular-monolith layout and narrow Podroid composition hook. |
| E03 | 2026-07-29 | `evidence/gates/B09.json` | Unit/integration tests; no authorized phone | SOFTWARE-PASS/HARDWARE-OPEN | Retain Ktor behind `HostControlServer`; do not generalize or replace it before live host-API evidence. |
| E04 | 2026-07-29 | `evidence/gates/B08.json` | Pinned official Android libtailscale build; no authorized phone | SOFTWARE-PASS/HARDWARE-OPEN | Retain Android-aware libtailscale/VpnService adapter; physical host-mesh evidence decides live viability. |
| E05 | 2026-07-29 | `evidence/gates/B11.json`, `B12.json` | No authorized phone | BLOCKED-HARDWARE | The physical guest vertical slice must test guest enrollment through SLIRP while host mesh is active. |
| E06 | 2026-07-29 | `evidence/gates/B04.json`, `B10.json`, F00 audit | Host/profile tests; no Android QEMU boot | SOFTWARE-PASS/FOUNDATION-OPEN/HARDWARE-OPEN | F01 must first make packaged JSON the production source; then repeated Android UEFI boot and guest access can close the live question. |
| E07 | 2026-07-29 | `evidence/gates/B06.json`, `B11.json`, `B20.json` | Bootstrap/recovery/redaction tests | SOFTWARE-PASS/HARDWARE-OPEN | Current one-use redemption design is retained; the physical guest slice must inspect actual guest persistence and logs. |
| E08 | 2026-07-29 | `evidence/gates/B14.json`, `evidence/T08/qa-summary.txt` | QMP/unit/integration tests | PASS | QMP is the lifecycle control boundary; physical shutdown remains part of device validation. |
| E09 | 2026-07-29 | `evidence/gates/B07.json`, `B16.json`, `B17.json` | No authorized phone/OEM matrix | BLOCKED-HARDWARE | No unattended-hosting reliability claim until Activity/service/process/reboot and actual controller-unavailable evidence pass. |
| E10 | — | `docs/architecture/debt-register.md` | — | DEFERRED | Qualified/trusted guests only until stronger process/UID isolation exists. |
| E11 | — | `docs/roadmap/acceptance-ledger.md` | — | BLOCKED-BASE-MVP | USB remains MVP+ and cannot enter executable scope before every base gate passes. |

Store full machine-readable output under ignored `.local/experiments/<ID>/` or attach it to CI/PR artifacts.
