# Small hardware-validation cycle

The software candidate is implemented. The fastest route to a validated MVP is one Linux workstation, one dedicated ARM64 phone, the existing Headscale lab, and the `tests/hil/` runner. Do not create a device farm or testing daemon before these scenarios demonstrate the need.

## H0 — consolidated physical path

Implemented by `tests/hil/`: one ignored configuration, explicit ADB serials, small Device/Controller/MeshLab ports, standard-library adapters, bounded redacted evidence, and compatibility wrappers for the old scripts.

```sh
cp tests/hil/config.example.json .local/hil.json
make lab-up
make hil-doctor
```

## H1 — QEMU smoke

```sh
make hil-smoke HIL_BUILD=1
```

This closes the physical part of B02 only when the exact APK starts the Alpine qualification profile, reaches real QMP-backed runtime readiness, has exactly one QEMU process, stops it, and restarts exactly one process. Do not normalize more Podroid arguments until H1 passes.

## H2 — useful MVP path

```sh
make hil-mvp
```

This exercises host Headscale identity, authenticated Host API, bounded image import or verified images, Ubuntu UEFI, distinct guest identity, ordinary key-only SSH, guest-mesh failure, and host-mediated recovery SSH. It is the evidence path for B08–B13.

## H3 — resilience

```sh
make hil-resilience
```

This exercises service restart, QEMU child death/reconciliation, and a controller-silent interval. Reboot is opt-in; a skipped reboot cannot close B16. The controller-silent smoke assertion demonstrates that desired state is not lease-driven, but B17 still requires evidence appropriate to the claimed duration and actual controller/network unavailability. H04 defines that distinction explicitly.

## MVP seal

After H1–H3 pass on one exact CI-built APK:

1. promote reviewed run evidence into `evidence/gates/`;
2. regenerate status with `make mvp-status`;
3. rerun automated suites;
4. title the release **MVP** only when every B01–B20 item is `PASS`;
5. only then allow USB/AOA MVP+ work.

## Deliberately deferred lab infrastructure

Add these only when repeated evidence requires them: Mobly, a lab daemon, leases, a second managed phone, UI Automator, controllable AP/network shaping, USB power switching, a remote self-hosted runner, or a device pool.
