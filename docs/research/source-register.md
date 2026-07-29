# Source register

This register records what was used to choose the scaffold. URLs are evidence; checked-in contracts and ADRs remain implementation authority.

## Podroid

- Repository: `https://github.com/ExTV/Podroid`
- Pinned MVP import: see `android/upstream/podroid.lock`.
- Relevant upstream areas: `QemuEngine.kt`, `QmpClient.kt`, `PodroidService.kt`, `EngineHolder.kt`, `podroid-launcher.c`, `build-all.sh`, native build Dockerfile, initramfs/rootfs scripts, kernel config.
- Key learning: QEMU is an ELF executable packaged in the APK native-library directory and launched with `ProcessBuilder`; preserve launcher/thread/socket behavior.

## Tailscale Android

- Repository: `https://github.com/tailscale/tailscale-android`
- Relevant areas: `libtailscale/interfaces.go`, Android `App.kt`, `IPNService.kt`, MDM/policy settings.
- Key learning: use Android-aware platform callbacks and `VpnService`, not generic desktop assumptions.
- Selected MVP line: Android release v1.98.2; its Tailscale core module declares Go 1.26.3. The Android repository commit remains an explicit T05 pinning gate.

## Headscale

- Versioned docs: `https://headscale.net/0.28.0/`
- Container docs and example config are used only for the disposable lab.
- Pre-authentication keys are used for noninteractive host/guest registration; administrative API keys stay on the controller.

## Android

- Android Studio/command-line tools: `https://developer.android.com/studio`
- AGP compatibility: `https://developer.android.com/build/releases/agp-9-1-0-release-notes`
- NDK installation: `https://developer.android.com/studio/projects/install-ndk`
- 16 KiB pages: `https://developer.android.com/guide/practices/page-sizes`
- foreground services: `https://developer.android.com/develop/background-work/services/fgs`
- Direct Boot: `https://developer.android.com/privacy-and-security/direct-boot`

## Guest/profile technologies

- QEMU ARM virt/QMP/qemu-img documentation: `https://www.qemu.org/docs/master/`
- cloud-init NoCloud: `https://cloudinit.readthedocs.io/`
- Ubuntu cloud images: `https://cloud-images.ubuntu.com/noble/current/`
- K3s requirements: `https://docs.k3s.io/installation/requirements`
- Kubernetes cgroup v2: `https://kubernetes.io/docs/concepts/architecture/cgroups/`

## Agent workflow

- OpenAI Codex/AGENTS guidance: official OpenAI Codex documentation and product guidance.
- The repository itself defines exact task packets, tests, and provenance requirements.
