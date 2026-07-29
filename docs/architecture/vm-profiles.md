# VM profiles

A profile describes compatible virtual hardware, boot artifacts, initialization, and qualification. It does not define cluster workloads.

## Qualified MVP profiles

### `alpine-direct-qualification`

Preserves the known Podroid direct-kernel path. It is a compatibility oracle and fallback, not a permanent Alpine dependency.

### `ubuntu-2404-arm64-uefi`

Proves distribution independence through an ARM64 cloud image, UEFI boot, virtio disks/network, serial console, NoCloud initialization, OpenSSH, and guest Tailscale enrollment.

### `k3s-worker-lab`

Derives from the Ubuntu profile and runs qualification checks only. It does not install or join K3s in the base MVP. The report checks the kernel, cgroup v2, namespaces, overlayfs, TUN, netfilter/bridge prerequisites, storage, memory, and network reachability needed for a later K3s worker profile.

## Compatibility contract

MVP generic cloud images must be ARM64, boot on QEMU `virt` with the selected UEFI firmware, support virtio block/network and serial console, support NoCloud, and permit OpenSSH plus Tailscale installation.

## Schema policy

- JSON is canonical.
- Unknown fields are rejected in v1alpha1.
- Artifact references require digest and expected size before activation.
- Profile bootstrap assets are trusted project code.
- No profile contains arbitrary host QEMU argv.
- Profile-specific guest scripts may execute only from checked-in, reviewed paths.

## Artifact locking

Mutable `current` image URLs may be used only by a pinning tool. The resulting digest, size, source URL, and fetch date go into `profiles/locks/images.lock.json`. Deployment consumes the lock, not the mutable URL.
