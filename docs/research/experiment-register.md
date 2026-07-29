# Experiment register

Append concise results here; do not paste full logs. `SOFTWARE-PASS/HARDWARE-OPEN` means the selected implementation and automated tests pass, but the research question still requires physical evidence.

| ID | Date | Source/evidence | Device/environment | Result | Decision impact |
|---|---|---|---|---|---|
| E01 | 2026-07-29 | `evidence/gates/B01.json`, `evidence/T08/qa-summary.txt` | Fedora build host | SOFTWARE-PASS | Podroid import, app build, and pinned runtime packaging are usable for device validation; project-owned native rebuild remains debt. |
| E02 | 2026-07-29 | `evidence/gates/B01.json`, Gradle module suites | Fedora build host | PASS | Keep sibling modular-monolith layout and narrow Podroid composition hook. |
| E03 | 2026-07-29 | `evidence/gates/B09.json` | Unit/integration tests; no authorized phone | SOFTWARE-PASS/HARDWARE-OPEN | Retain Ktor behind `HostControlServer`; do not generalize or replace it before D02. |
| E04 | 2026-07-29 | `evidence/gates/B08.json` | Pinned official Android libtailscale build; no authorized phone | SOFTWARE-PASS/HARDWARE-OPEN | Retain Android-aware libtailscale/VpnService adapter; D02 decides live viability. |
| E05 | 2026-07-29 | `evidence/gates/B11.json`, `B12.json` | No authorized phone | BLOCKED-HARDWARE | D03 must test guest enrollment through SLIRP while host mesh is active. |
| E06 | 2026-07-29 | `evidence/gates/B04.json`, `B10.json` | Host/profile tests; no Android QEMU boot | SOFTWARE-PASS/HARDWARE-OPEN | Keep AAVMF/Ubuntu profile provisional until D03 repeated boot and SSH. |
| E07 | 2026-07-29 | `evidence/gates/B06.json`, `B11.json`, `B20.json` | Bootstrap/recovery/redaction tests | SOFTWARE-PASS/HARDWARE-OPEN | Current one-use redemption design is retained; D03 must inspect actual guest persistence and logs. |
| E08 | 2026-07-29 | `evidence/gates/B14.json`, `evidence/T08/qa-summary.txt` | QMP/unit/integration tests | PASS | QMP is the lifecycle control boundary; physical shutdown remains part of D01/D03. |
| E09 | 2026-07-29 | `evidence/gates/B07.json`, `B16.json`, `B17.json` | No authorized phone/OEM matrix | BLOCKED-HARDWARE | No unattended-hosting reliability claim until D05. |
| E10 | — | `docs/architecture/debt-register.md` | — | DEFERRED | Qualified/trusted guests only until stronger process/UID isolation exists. |
| E11 | — | `docs/roadmap/acceptance-ledger.md` | — | BLOCKED-BASE-MVP | USB remains MVP+ and cannot enter executable scope before D07. |

Store full machine-readable output under ignored `.local/experiments/<ID>/` or attach it to CI/PR artifacts.
