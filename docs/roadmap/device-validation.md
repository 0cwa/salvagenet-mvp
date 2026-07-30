# Small hardware-validation path

The repository is a software-qualified device-lab candidate. The fastest physical route remains one Linux workstation, one dedicated ARM64 phone, the existing Headscale lab, and the single `tests/hil/` runner. Do not create a device farm or testing daemon before repeated scenarios demonstrate the need.

## Relationship to implementation phases

Physical validation is not one final waterfall step:

- run the smallest useful scenario during a phase when a device is available;
- treat a run as diagnostic when later runtime work changes the tested APK semantics;
- record unavailable checks honestly at phase end;
- re-run the full gate-relevant sequence against one exact final candidate before the MVP seal.

F01 is merged, so packaged profile and active-manifest semantics are now stable. H02A qualifies the Ubuntu guest path on Linux host QEMU only; it cannot close Android gates. A phone run during H02A is still useful diagnostic evidence, but final B10–B12 evidence must be rerun against the eventual exact candidate.

## H0 — consolidated physical path

Implemented by `tests/hil/`: one ignored configuration, explicit ADB serials, small Device/Controller/MeshLab ports, standard-library adapters, bounded redacted evidence, and compatibility wrappers for the old scripts.

```sh
cp tests/hil/config.example.json .local/hil.json
make lab-up
make hil-doctor
```

## H1 — device substrate smoke

```sh
make hil-smoke HIL_BUILD=1
```

This supports B02 only when the exact APK starts the Alpine qualification profile, reaches real QMP-backed runtime readiness, has exactly one QEMU process, stops it, and restarts exactly one process. During a runtime-changing phase, record the result as diagnostic and rerun on the final candidate.

## H2 — useful guest vertical slice

```sh
make hil-mvp
```

This exercises host Headscale identity, authenticated Host API, bounded artifact upload/import, Ubuntu UEFI, distinct guest identity, ordinary key-only SSH, guest-mesh failure, and host-mediated recovery SSH. It is the physical evidence path for B08–B13.

Before promoting B10–B12, confirm the evidence identifies the exact packaged profile and artifact manifest/digest used by the APK rather than only a similarly named host-QEMU profile.

## H3 — durability and independence

```sh
make hil-resilience
```

This exercises service restart, QEMU child death/reconciliation, and a controller-silent interval. Reboot is opt-in; a skipped reboot cannot close B16. The controller-silent smoke demonstrates that desired state is not lease-driven, but B17 requires evidence appropriate to the claimed duration and actual controller/network unavailability.

## MVP seal

After the relevant foundations and fixes have landed, run H1–H3 on one exact green CI-built APK:

1. verify all phase acceptance/exit criteria that affect the candidate;
2. promote reviewed run evidence into `evidence/gates/`;
3. regenerate status with `make mvp-status`;
4. rerun automated suites;
5. title the release MVP only when every B01–B20 item is PASS;
6. only then activate USB/AOA MVP+ work.

## Deliberately deferred lab infrastructure

Add these only when repeated evidence requires them: Mobly, a lab daemon, leases, a second managed phone, UI Automator, controllable AP/network shaping, USB power switching, a remote self-hosted runner, or a device pool.
