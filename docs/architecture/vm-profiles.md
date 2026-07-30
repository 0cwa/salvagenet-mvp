# VM profiles

A profile describes compatible virtual hardware, boot artifacts, initialization, and qualification. It does not define cluster workloads.

## Current implementation truth

Checked-in JSON is the intended canonical format and already passes schema/guest validation. The Android runtime currently mirrors the three profile definitions in Kotlin inside `AndroidQemuProfileStorage`; the mirror is not the permanent contract and does not contain every checked-in JSON field identically.

F01 removes this split source of truth by packaging and loading the validated JSON in production. Until F01 passes, host-QEMU profile evidence narrows guest/image problems but does not prove that the APK resolved the exact same profile data.

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

- JSON becomes the sole production source of truth when F01 exits successfully.
- Unknown fields are rejected in v1alpha1.
- Unsupported versions and unresolved inheritance fail before QEMU or filesystem effects.
- Artifact references require digest and expected size before activation.
- Profile bootstrap assets are trusted project code and must be packaged exactly with the profile that names them.
- No profile contains arbitrary host QEMU argv.
- Profile-specific guest scripts may execute only from checked-in, reviewed paths.

## Artifact locking

Mutable `current` image URLs may be used only by a pinning tool. The resulting digest, size, source URL, and fetch date go into `profiles/locks/images.lock.json`. Deployment consumes the lock, not the mutable URL.

Published artifact manifests are versioned project data. Publication, listing, and runtime consumption must agree on exact fields, digest, expected size, immutable relative path, and root containment; F01 establishes the shared consumer contract.
