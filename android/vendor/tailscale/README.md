# Pinned official Android libtailscale

T05 integrates the headless platform layer from the official
[`tailscale/tailscale-android`](https://github.com/tailscale/tailscale-android)
repository. `tailscale.lock` pins both that Android source and Tailscale core to
immutable commits. The upstream BSD-3-Clause license is retained as `LICENSE`.
No upstream UI, account screens, Taildrop UI, or generated binary is committed.

## Reproducible binding

Prerequisites are Go 1.26.3, JDK 17, Android SDK/NDK, Git, and network access to
the two pinned GitHub repositories. From the repository root:

```sh
source ~/.config/nodehost/env.sh
export PATH="$HOME/.local/nodehost/venv/bin:$PATH"
tools/vendor/build-libtailscale-android.sh
```

The script verifies Go, checks out Android commit
`68dd0a5170999fa33c884cb58a8d1679234cc9a3`, resolves core tag `v1.98.2` to
`34c530668cb05fa60b3d707a44b70460344789ef`, installs the source-pinned
`gomobile`/`gobind`, and runs the official binding shape:

```sh
gomobile bind -target android/arm64 -androidapi 26 \
  -ldflags "-linkmode=external -extldflags=-Wl,-z,max-page-size=16384" \
  -o android/vendor/tailscale/build/libtailscale.aar ./libtailscale
```

The project intentionally omits upstream's `tailscale_go` optimization tag
because that tag requires Tailscale's patched Go runtime; the pinned standard
Go 1.26.3 build uses the supported fallback synchronization implementation.
The MVP target is ARM64. Gradle invokes the script when the ignored AAR is
absent or stale. All clones, Go tools, generated Java, native libraries, and
AARs remain under ignored `android/vendor/tailscale/build/`.
