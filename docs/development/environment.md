# Development environment

## Pinned baseline

The first overnight run mirrors the imported Podroid toolchain instead of upgrading it simultaneously:

- JDK 17;
- Gradle 9.3.1 through the imported wrapper;
- Android Gradle Plugin 9.1.x from the imported version catalog;
- compile/target SDK 36 family;
- Android build tools 36.0.0;
- NDK r27c (`27.2.12479018`) for Podroid parity;
- Python 3.12+ for repository tooling and the MVP controller;
- Go 1.26.3 for the selected Tailscale v1.98.2/libtailscale baseline;
- Docker or Podman for Podroid native builds and the Headscale lab;
- ADB plus udev authorization for a physical ARM64 phone.

Do not upgrade AGP/Kotlin/NDK during the base-MVP night unless the imported Podroid baseline cannot build. Record an upgrade as a separate commit and experiment.

## Host versus container

Use the host for Android SDK, ADB, USB, KVM/emulator, and Docker daemon authorization. The devcontainer is useful for docs, schemas, Python tools, and code review but mounts or delegates host services for Android/device work.

## Tool tiers

### Required before overnight

`git`, `bash`, `python3`, JDK 17, Go 1.26.3, Docker/Podman, Android SDK command-line tools, SDK platform/build tools, NDK r27c, ADB, `curl`, `jq`, `make`, `unzip`, `zip`, `openssl`.

### Recommended

`shellcheck`, `shfmt`, `yamllint`, `pre-commit`, `ripgrep`, `fd`, `tmux`, `direnv` or `mise`.

### Optional/post-MVP

Rust for the later controller/hostd, Slint tooling, `syft`, `cosign`, `tuf`, `oras`.

## Validation

Run:

```sh
make doctor
make validate
make goal-preflight
```

The doctor distinguishes missing tools, missing authorization, and intentionally absent Podroid/device assets.
