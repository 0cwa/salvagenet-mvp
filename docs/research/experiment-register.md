# Experiment register

Append concise results here; do not paste full logs. `SOFTWARE-PASS/HARDWARE-OPEN` means the selected implementation and automated tests pass, but the research question still requires physical evidence.

| ID | Date | Source/evidence | Device/environment | Result | Decision impact |
|---|---|---|---|---|---|
| F00 | 2026-07-30 | `docs/research/experiments/F00.md`, PR #6, Actions run `30524125036` | Repository and GitHub CI | PASS | Phase 0 passed: completed tasks are historical, future work is queued by default, and phase-boundary acceptance verification is enforced. |
| F01 | 2026-07-30 | `docs/research/experiments/F01.md`, PR #7, merge `246d551ca7e691a0319a4b30e29d6e4905cd9910`, Actions run `30549498423` | Repository, Android build, package artifact | PASS | Packaged profile JSON and strict active manifests are production truth. Remove the unused pre-release migration; split the former H02 into guest boot and guest mesh phases. |
| H02A | — | `docs/research/experiments/H02A.md` | Linux host QEMU | PLANNED | Qualify UEFI/QMP, NoCloud, key-only loopback SSH, restart, and secret hygiene before guest mesh work. |
| H02B | — | `docs/research/experiments/H02B.md` | Linux host QEMU + disposable Headscale | QUEUED_REVIEW | Activate only if H02A passes and guest mesh remains the highest-value uncertainty. |
| E01 | 2026-07-29 | `evidence/gates/B01.json`, `evidence/T08/qa-summary.txt` | Fedora build host | SOFTWARE-PASS | Podroid import, app build, and pinned runtime packaging are usable for device validation; project-owned native rebuild remains debt. |
| E02 | 2026-07-29 | `evidence/gates/B01.json`, Gradle module suites | Fedora build host | PASS | Keep sibling modular-monolith layout and narrow Podroid composition hook. |
| E03 | 2026-07-29 | `evidence/gates/B09.json` | Unit/integration tests; no authorized phone | SOFTWARE-PASS/HARDWARE-OPEN | Retain Ktor behind `HostControlServer`; do not generalize or replace it before live host-API evidence. |
| E04 | 2026-07-29 | `evidence/gates/B08.json` | Pinned official Android libtailscale build; no authorized phone | SOFTWARE-PASS/HARDWARE-OPEN | Retain Android-aware libtailscale/VpnService adapter; physical host-mesh evidence decides live viability. |
| E05 | 2026-07-29 | `evidence/gates/B11.json`, `B12.json` | No authorized phone | BLOCKED-HARDWARE | The physical guest vertical slice must test guest enrollment through SLIRP while host mesh is active. H02B may reduce guest-side ambiguity first. |
| E06 | 2026-07-29 | `docs/research/experiments/F01.md`, H02A packet | Canonical packaged profile; host-QEMU evidence pending | SOFTWARE-SOURCE-CLOSED/HOST-OPEN/HARDWARE-OPEN | F01 closed the source-of-truth question. H02A must qualify the real host Ubuntu boot path; Android boot remains physical evidence. |
| E07 | 2026-07-29 | `evidence/gates/B06.json`, `B11.json`, `B20.json` | Bootstrap/recovery/redaction tests | SOFTWARE-PASS/GUEST-INSPECTION-OPEN/HARDWARE-OPEN | H02A must inspect a real host-QEMU guest; the physical guest slice must later inspect Android-bound diagnostics and retries. |
| E08 | 2026-07-29 | `evidence/gates/B14.json`, `evidence/T08/qa-summary.txt` | QMP/unit/integration tests | PASS | QMP is the lifecycle control boundary; host and physical graceful shutdown remain validation steps. |
| E09 | 2026-07-29 | `evidence/gates/B07.json`, `B16.json`, `B17.json` | No authorized phone/OEM matrix | BLOCKED-HARDWARE | No unattended-hosting reliability claim until Activity/service/process/reboot and actual controller-unavailable evidence pass. |
| E10 | — | `docs/architecture/debt-register.md` | — | DEFERRED | Qualified/trusted guests only until stronger process/UID isolation exists. |
| E11 | — | `docs/roadmap/acceptance-ledger.md` | — | BLOCKED-BASE-MVP | USB remains MVP+ and cannot enter executable scope before every base gate passes. |

Store full machine-readable output under ignored `.local/experiments/<ID>/` or attach it to CI/PR artifacts.
