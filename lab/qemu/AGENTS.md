# Host QEMU laboratory instructions

- This lab qualifies canonical profile artifacts and guest initialization independently of Android execution; it cannot replace the physical APK-native QEMU gate.
- H02A must consume the canonical Ubuntu profile and rendered vendor-data. Do not maintain a second complete profile or hand-authored replacement vendor-data.
- A test-only NoCloud user-data layer may supply an ephemeral SSH public key and mesh-independent readiness marker. It must not create `/var/lib/nodehost/bootstrap.env` or introduce NodeHost or guest-mesh authentication keys, bootstrap tokens, callback capabilities, Headscale, or Tailscale.
- Normal runs consume the pinned Ubuntu lock without mutating it. Pin updates are explicit reviewed changes.
- Record selected AAVMF paths, digests, sizes, and host package/tool facts before QEMU starts; do not imply byte identity with Android artifacts unless proven.
- Keep downloaded images, overlays, firmware copies, keys, sockets, PID files, and logs under ignored `.local/qemu-lab/`.
- Keep evidence bounded and redacted. Explicitly classify it as host-QEMU, not Android or physical-gate evidence.
- Use only loopback host forwarding. Never commit generated SSH private keys.
- H02B owns guest mesh behavior. Do not add Headscale/Tailscale assertions to H02A scripts.
