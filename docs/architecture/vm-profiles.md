# VM profiles

A profile describes compatible virtual hardware, boot artifacts, initialization, and qualification. It does not define cluster workloads.

## Current implementation truth

Checked-in JSON is the canonical profile format. The build generates a bounded profile index, packages the index, schema, exact profile documents, and required guest-init assets, and verifies their bytes in the APK. Android consumes that packaged index and strictly decodes the documents it names before QEMU or mutable disk effects. A complete Kotlin profile mirror is prohibited.

Artifact publication, listing, cleanup, installed checks, and runtime consumption share one strict active-manifest contract. Ubuntu, AAVMF, and every other non-Podroid artifact require an active manifest. Only the three pinned Podroid qualification inputs retain their narrowly scoped packaged bare-file plus `.sha256` adapter.

H02A tests the same canonical Ubuntu profile and guest-init inputs used by the Android runtime. Host-QEMU evidence still cannot prove APK-native Android execution, but it no longer tests a parallel profile definition.

## Qualified MVP profiles

### `alpine-direct-qualification`

Preserves the known Podroid direct-kernel path. It is a current packaging and qualification oracle for APK-native QEMU behavior, not a permanent Alpine dependency.

### `ubuntu-2404-arm64-uefi`

Proves distribution independence through an ARM64 cloud image, UEFI boot, virtio disks/network, serial console, NoCloud initialization, OpenSSH, and later guest Tailscale enrollment.

The current MVP creates a digest-verified writable copy of the imported qcow2 source. The profile therefore names this mode `copied-writable`; it does not claim a qcow2 backing-file overlay.

H02A qualifies boot, QMP, NoCloud, key-only loopback SSH, restart, and secret hygiene. Guest Tailscale is a separate H02B concern.

### `k3s-worker-lab`

Records `derivedFrom: ubuntu-2404-arm64-uefi` as provenance and runs qualification checks only. `derivedFrom` does not perform inheritance or merging: every runtime field remains explicit in the derived profile and CI checks that its shared hardware sections match Ubuntu. The profile does not install or join K3s in the base MVP. Its report checks the kernel, cgroup v2, namespaces, overlayfs, TUN, netfilter/bridge prerequisites, storage, memory, and network reachability needed for a later K3s worker profile.

## Compatibility contract

MVP generic cloud images must be ARM64, boot on QEMU `virt` with the selected UEFI firmware, support virtio block/network and serial console, support NoCloud, and permit OpenSSH plus later Tailscale installation.

## Schema policy

- JSON and the generated packaged index are the sole production profile registry and source of truth.
- Unknown fields are rejected in v1alpha1.
- Unsupported versions, unavailable derivation references, and inconsistent index digests fail before QEMU or filesystem effects.
- `derivedFrom` is provenance, not runtime inheritance.
- Artifact references require digest and expected size before activation.
- Non-Podroid artifacts require valid active manifests.
- Profile bootstrap assets are trusted project code and must be packaged exactly with the profile that names them.
- Vendor-data paths reject empty, `.` and `..` segments before asset access.
- No profile contains arbitrary host QEMU argv.
- Profile-specific guest scripts may execute only from checked-in, reviewed paths.

## Artifact locking

Mutable `current` image URLs may be used only by a pinning tool. The resulting digest, size, source URL, and fetch date go into `profiles/locks/images.lock.json`. Deployment consumes the lock, not the mutable URL.

Published artifact manifests are versioned project data. Publication, listing, cleanup, installed checks, and runtime consumption agree on exact fields, digest, expected size, immutable relative path, payload size, and root containment.
