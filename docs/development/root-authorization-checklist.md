# Root and authorization checklist

Run these steps yourself before handing the repository to an overnight agent.
The project scripts never invoke `sudo` silently.

## 1. Host packages, groups, and container runtime

```sh
sudo tools/bootstrap/ubuntu-root-setup.sh
```

The script installs the Android/native/test prerequisites, adds the invoking
user to `docker` and `plugdev` when those groups exist, and enables Docker.
Log out and back in once so the group changes apply. Then verify:

```sh
docker run --rm hello-world
adb version
java -version
```

On a non-Ubuntu host, use `docs/development/environment.md` as the package list
and keep the same pinned Android toolchain.

## 2. Go and Android SDK as the development user

```sh
tools/bootstrap/install-go.sh
tools/bootstrap/install-android-sdk.sh
source "$HOME/.config/nodehost/env.sh"
yes | sdkmanager --licenses
```

Go 1.26.3 is pinned because the selected Tailscale v1.98.2 core module declares
that toolchain. The Android installer selects JDK 17 explicitly instead of
inheriting the host's current `javac` alternative.

The installer verifies the command-line-tools archive checksum and installs the
pinned SDK platform, build tools, NDK, and CMake packages. It does not require
root.

## 3. ADB and physical-device authorization

- Enable developer options and USB debugging on the ARM64 phone.
- Connect directly and accept the RSA authorization dialog.
- Require `adb devices -l` to show `device`, not `unauthorized`.
- Reconnect the device after group/udev changes.

```sh
make device-facts
```

Keep the phone charged and thermally safe; do not run indefinite load tests on
battery.

## 4. Android VPN approval

Embedded Tailscale uses Android `VpnService`. The first interactive build needs
one on-device approval. Ordinary stock Android does not offer a root script to
pre-authorize this safely.

## 5. Headscale laboratory reachability

```sh
cp lab/headscale/.env.example lab/headscale/.env
# Set HEADSCALE_PUBLIC_URL=http://<host-lan-ip>:8080
make lab-up
make lab-keys
make lab-status
```

The renderer rejects placeholder and non-phone-reachable addresses. Open the
health URL from the phone before starting host-mesh work. Live keys stay in
ignored `lab/headscale/secrets/` files.

## 6. Podroid/native build resources

The first QEMU/kernel/rootfs build is container- and disk-intensive. Reserve at
least 30 GiB of free workspace and verify that the authorized container runtime
can pull images. This is an operational recommendation, not a domain contract.

## 7. Git, hooks, and worktrees

```sh
make install-hooks
make integration-worktree
make goal-preflight
```

The overnight runner needs write access to the repository and `.worktrees/`, but
must not receive signing keys, Headscale administrative credentials, or broad
root access.

## 8. Secret locations

Create live files only under ignored paths:

```text
.local/
lab/headscale/secrets/
control/examples/local/
controller/mvp-cli/controller.json
```

Never paste live auth keys into task packets, AGENTS files, commit messages,
model prompts, or acceptance evidence.
