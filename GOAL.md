# Goal: functional Podroid-fork node-host MVP

## Outcome

Produce a debug-signed Android APK that preserves Podroid's APK-native QEMU execution path while adding a durable node supervisor, profile-driven VM deployment, Headscale/Tailscale host and guest enrollment, imported controller/SSH authorization, and typed remote VM lifecycle control.

## Base MVP success conditions

- Podroid is imported at the pinned commit and still boots its known-good QEMU guest on one physical ARM64 Android device.
- QEMU launch behavior is represented by a typed command compiler; no public API accepts raw QEMU or kernel arguments.
- The implementation retains all useful upstream argument/launcher knowledge in `docs/architecture/qemu-command-knowledge.md` and snapshot tests.
- One active VM can be created from either:
  - the known-good direct-kernel Alpine qualification profile; or
  - a generic ARM64 UEFI/cloud-image profile.
- A third `k3s-worker-lab` profile proves Kubernetes/K3s prerequisites and emits a qualification report; joining a cluster is not part of base MVP.
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

After every base-MVP gate is green, a Linux/SBC host can optionally provide a QEMU `eth1` link over Android Open Accessory USB, with SLIRP remaining the fallback path.

## Explicit non-goals for the overnight run

- Multiple active VMs.
- Kubernetes, Swarm, or Nomad orchestration inside the Android application.
- Production artifact update framework or delegated trust.
- A polished Slint controller.
- Device Owner or patched-Android deployment.
- Arbitrary ISO installers, x86 guests, graphical desktops, audio, or broad USB passthrough.
- Perfect abstractions, comprehensive migrations, or production-grade cryptographic enrollment.

## Quality rule

Prefer the simplest functional implementation that preserves the module boundaries and acceptance criteria. Mark known hardening work with scoped comments:

```text
TODO(MVP-HARDENING, Txx): concrete improvement and why it is deferred.
```

Do not use vague TODOs. Do not solve deferred work while a base-MVP acceptance criterion is still red.
