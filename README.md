# NodeHost MVP

NodeHost turns an ARM64 Android device into a remotely managed, profile-driven QEMU host. The Android application owns host identity, durable desired state, QEMU lifecycle, host-mesh connectivity, recovery access, and a typed Host API. Guest configuration remains the job of ordinary SSH and provisioning tools.

> **Current maturity: device-lab candidate, not yet a validated MVP.**
>
> The software, packaging, and simulated integration gates are substantially implemented. The remaining base gates require an authorized physical ARM64 Android device and a live Headscale/guest-network vertical slice.

<!-- MVP-STATUS-BEGIN -->
**Acceptance:** 10/20 base gates passed; 10 are blocked on physical-device validation. USB networking remains deferred until every base gate passes.
<!-- MVP-STATUS-END -->

See [`docs/STATUS.md`](docs/STATUS.md) for the generated gate breakdown and [`docs/roadmap/device-validation.md`](docs/roadmap/device-validation.md) for the next development cycle.

## Implemented candidate

- Podroid-derived APK-packaged QEMU and launcher integration.
- Typed QEMU command compilation, bounded diagnostics, QMP control, graceful shutdown, and one-VM reconciliation.
- Alpine direct-kernel, Ubuntu ARM64 UEFI, and K3s-worker qualification profiles.
- Room-backed desired state and operation journal with crash/retry tests.
- Imported enrollment, controller authorization, embedded Android-aware `libtailscale`, typed HTTPS Host API, guest bootstrap, and recovery SSH proxy.
- Agent-scoped task packets, evidence records, provenance trailers, static checks, Android/JVM tests, and packaging checks.

## Still required for the base MVP

The physical vertical slice must prove:

1. APK-native QEMU boot on an ARM64 Android device.
2. host Tailscale/Headscale enrollment and authenticated Host API reachability;
3. controller-driven Ubuntu deployment and independent guest mesh enrollment;
4. ordinary guest SSH and host-mediated recovery SSH;
5. Activity/service/process/reboot recovery and controller-offline continuity.

Do not begin USB/AOA networking while any base gate remains incomplete.

## Start here

```sh
cat GOAL.md
cat AGENTS.md
cat docs/STATUS.md
make doctor
make validate
```

For physical-device work, read [`agents/device-validation-goal.md`](agents/device-validation-goal.md) and the nearest nested `AGENTS.md` files rather than reusing the completed overnight implementation packets blindly.

## Common commands

```sh
make validate             # repository, contracts, evidence, and static checks
make test-jvm             # pure model/application tests
make test-android         # Android adapter tests and lint
make test-guest           # guest/profile qualification tests
make mvp-status           # regenerate docs/STATUS.md and the README summary
make lab-up               # disposable Headscale laboratory
make device-facts         # collect facts from an authorized Android device
```

## Repository map

| Need | Canonical source |
|---|---|
| Product boundary and success conditions | [`GOAL.md`](GOAL.md) |
| Current acceptance state | [`docs/STATUS.md`](docs/STATUS.md) |
| Acceptance evidence | [`docs/roadmap/acceptance-ledger.md`](docs/roadmap/acceptance-ledger.md) and `evidence/gates/` |
| Architecture and module boundaries | [`docs/architecture/overview.md`](docs/architecture/overview.md), [`docs/architecture/module-map.md`](docs/architecture/module-map.md) |
| Known debt and expiry triggers | [`docs/architecture/debt-register.md`](docs/architecture/debt-register.md) |
| Physical-device sequence | [`docs/roadmap/device-validation.md`](docs/roadmap/device-validation.md) |
| Development environment | [`HANDOFF.md`](HANDOFF.md), [`docs/development/environment.md`](docs/development/environment.md) |
| Complete documentation index | [`docs/INDEX.md`](docs/INDEX.md) |

## Historical scaffold material

`SCAFFOLD-MANIFEST.md`, `VALIDATION.md`, and the T00–T08 overnight packets document how the initial implementation was produced. They are historical provenance, not the current product-status authority. The acceptance ledger and generated status page are authoritative.
