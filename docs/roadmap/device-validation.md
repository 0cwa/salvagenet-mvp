# Small hardware-validation cycle

The software candidate is implemented. The fastest route to a validated MVP is one Linux workstation, one dedicated ARM64 phone, the existing Headscale lab, and the `tests/hil/` runner. Do not create a device farm or testing daemon before these scenarios demonstrate the need.

## H0 — consolidate the physical test path

Implemented by `tests/hil/`:

- one ignored `.local/hil.json` configuration;
- explicit device serial on every ADB command;
- small Device, Controller, and MeshLab ports;
- standard-library Python adapters;
- bounded redacted evidence under `.local/hil-runs/`;
- old E2E/device scripts reduced to wrappers.

Run:

```sh
cp tests/hil/config.example.json .local/hil.json
make lab-up
make hil-doctor
```

## H1 — QEMU smoke

```sh
make hil-smoke HIL_BUILD=1
```

This closes the physical part of B02 only when the run proves the exact APK starts the Alpine qualification profile, reaches successful runtime operation/QMP readiness, has exactly one QEMU process, stops it, and restarts exactly one process.

Do not normalize or remove more Podroid QEMU arguments until H1 passes on hardware.

## H2 — complete useful MVP path

```sh
make hil-mvp
```

This exercises:

```text
host Headscale identity
-> authenticated Host API
-> bounded image import / existing verified images
-> Ubuntu UEFI profile
-> distinct guest Headscale identity
-> ordinary key-only SSH
-> guest mesh disabled
-> host-mediated recovery SSH
```

It is the evidence path for B08–B13. The config names exact host/guest nodes and required artifact IDs; secrets remain in the existing ignored controller/lab files.

## H3 — resilience

```sh
make hil-resilience
```

This exercises service restart, QEMU child death/reconciliation, and a period with no controller requests. Reboot is opt-in in `.local/hil.json`; a skipped reboot remains explicitly skipped and cannot close B16.

This is the evidence path for B07, B16, and B17, with the exact disturbance named in the assertion record.

## MVP seal

After H1–H3 pass on one exact CI-built APK:

1. promote reviewed run evidence into `evidence/gates/`;
2. regenerate `docs/STATUS.md` and README with `make mvp-status`;
3. rerun `make validate` and the automated suites;
4. title the release **MVP** only when every B01–B20 item is `PASS`;
5. only then allow executable USB/AOA MVP+ work.

## Deliberately deferred lab infrastructure

Add these only when a repeated requirement proves them necessary: Mobly, a lab daemon, device leases, a second managed phone, UI Automator, controllable AP/network shaping, USB power switching, remote self-hosted runners, or a device pool.
