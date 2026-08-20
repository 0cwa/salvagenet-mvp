# Current milestone: validated stock-Android QEMU node substrate

## Relationship to the SalvageNet product

This file defines the bounded current implementation and acceptance milestone. The durable product direction is [`docs/product/north-star.md`](docs/product/north-star.md).

The current milestone proves that an ordinary old Android phone can become a durable, remotely provisioned Linux-capable node host without requiring root or a custom ROM. It intentionally stops before the first turnkey orchestrator attachment so the APK/QEMU, lifecycle, network, recovery, and evidence semantics can be validated independently.

The next accepted product milestone is described in [`docs/roadmap/strategic-priorities.md`](docs/roadmap/strategic-priorities.md): one signed configuration attaches the validated stock node to Docker Engine Swarm mode through native configuration, with a thin Slint controller and minimum unattended safety floor. That later work is visible in the roadmap but is not current implementation authorization.

## Outcome

Produce a debug-signed Android APK that preserves Podroid's APK-native QEMU execution path while adding a durable node supervisor, profile-driven VM deployment, Headscale/Tailscale host and guest enrollment, imported controller/SSH authorization, and typed remote VM lifecycle control.

## Base milestone success conditions

- Podroid is imported at the pinned commit and still boots its known-good QEMU guest on one physical ARM64 Android device.
- QEMU launch behavior is represented by a typed command compiler; no public API accepts raw QEMU or kernel arguments.
- The implementation retains all useful upstream argument/launcher knowledge in `docs/architecture/qemu-command-knowledge.md` and snapshot tests.
- One active VM can be created from either:
  - the known-good direct-kernel Alpine qualification profile; or
  - a generic ARM64 UEFI/cloud-image profile.
- A third `k3s-worker-lab` profile proves Kubernetes/K3s prerequisites and emits a qualification report; joining a cluster is not part of this bounded milestone.
- A versioned enrollment JSON file installs:
  - Headscale control URL and one-use host key;
  - controller API credential/trust data;
  - guest SSH user-CA or authorized key material;
  - artifact/profile defaults.
- The Android host joins Headscale through the in-app Tailscale adapter.
- The guest independently joins Headscale using an expiring one-use key.
- The controller can import an image and apply desired VM state through the host API.
- The controller reaches the guest through ordinary SSH; a host-mediated recovery path exists when guest mesh enrollment fails.
- Activity destruction, controller disconnection, and a normal service restart do not redefine desired VM state.
- Deployment operations are persisted and idempotent enough to resume or safely fail after process death.
- No default password, unauthenticated LAN service, raw QMP endpoint, or arbitrary shell endpoint exists.

## MVP+ success condition

After every base-milestone gate is green, a Linux/SBC host can optionally provide a QEMU `eth1` link over Android Open Accessory USB, with SLIRP remaining the fallback path.

USB remains separately gated. Its implementation order may be re-evaluated against the turnkey-cluster milestone, but it must not delay the ordinary physical node proof.

## Explicit non-goals for this milestone

- Multiple active VMs.
- Kubernetes, Swarm, or Nomad orchestration inside the Android application.
- A universal cluster or workload configuration model.
- Production artifact update framework or delegated trust.
- A polished Slint controller.
- Device Owner or patched-Android deployment.
- AVF, native Linux/SBC/WSL backends, or a custom Linux OS.
- Zenoh bootstrap/discovery integration.
- QR/account enrollment or personal-storage policy.
- Arbitrary ISO installers, x86 guests, graphical desktops, audio, or broad USB passthrough.
- Perfect abstractions, comprehensive migrations, or production-grade cryptographic enrollment.

These are milestone exclusions, not rejections of the durable product direction. Accepted later outcomes belong in the GitHub roadmap and north-star documents.

## Quality rule

Prefer the simplest functional implementation that preserves the module boundaries and acceptance criteria. Mark known hardening work with scoped comments:

```text
TODO(MVP-HARDENING, Txx): concrete improvement and why it is deferred.
```

Do not use vague TODOs. Do not solve deferred work while a base acceptance criterion is still red unless a reviewed phase boundary demonstrates that it blocks the physical proof or creates a direct security/correctness failure.

## Current critical path

1. finish the bounded H02A canonical Ubuntu host-QEMU qualification;
2. move immediately to the one-phone physical sequence through `tests/hil/`;
3. prove host mesh/API, remote Ubuntu deployment, guest mesh/SSH, recovery, lifecycle, reboot, and controller-offline behavior;
4. bind B01–B20 to one exact source commit and APK;
5. only then activate the smallest next roadmap phase justified by evidence.

`agents/task-dag.json` and the active task packet remain the implementation authority. This file does not authorize the queued strategic roadmap.
