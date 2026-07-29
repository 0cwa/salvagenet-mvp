#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run explicitly with sudo: sudo $0" >&2; exit 2; }
user=${SUDO_USER:-root}
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl git git-lfs jq make openssl \
  python3 python3-venv python3-pip python3-jsonschema \
  unzip zip rsync shellcheck shfmt yamllint \
  openjdk-17-jdk-headless \
  docker.io docker-compose-v2 \
  adb android-sdk-platform-tools-common \
  qemu-system-arm qemu-system-x86 qemu-kvm qemu-utils qemu-efi-aarch64 cloud-image-utils \
  libusb-1.0-0-dev build-essential pkg-config ninja-build meson cmake \
  iproute2 nftables socat netcat-openbsd \
  tmux ripgrep fd-find

if getent group plugdev >/dev/null; then usermod -aG plugdev "$user"; fi
if getent group docker >/dev/null; then usermod -aG docker "$user"; fi
if getent group kvm >/dev/null; then usermod -aG kvm "$user"; fi
systemctl enable --now docker 2>/dev/null || true

cat <<MSG
Root package setup complete for user: $user
Log out and back in for docker/plugdev/kvm group changes, then run as that user:
  tools/bootstrap/install-go.sh
  tools/bootstrap/install-android-sdk.sh
  source ~/.config/nodehost/env.sh
  make doctor
MSG
