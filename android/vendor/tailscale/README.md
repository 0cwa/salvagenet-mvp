# Tailscale Android vendor slot

T05 pins and imports only the official Android-aware `libtailscale` and required platform integration from `tailscale/tailscale-android`. The scaffold contains no third-party source.

Required before implementation:

1. verify/update `tailscale.lock` to an immutable upstream tag/commit;
2. retain BSD license and source provenance;
3. document the exact `gomobile bind` or upstream Gradle generation command;
4. keep upstream UI/Taildrop/account screens out of the node-host module;
5. place generated local artifacts under ignored `android/vendor/tailscale/build/`.

Toolchain baseline:

- Go 1.26.3 (declared by Tailscale core v1.98.2); install with `tools/bootstrap/install-go.sh`.
- The Android repository's full immutable commit remains a T05 closure item; do not substitute the core repository commit.
