# Human-to-agent handoff

This is the shortest safe route from the clean scaffold to an overnight goal
run. Complete the **Human** section yourself; then give the runner `GOAL.md` and
`agents/overnight-goal.md`, not the full documentation tree.

## Human: one-time host authorization

```sh
sudo tools/bootstrap/ubuntu-root-setup.sh
# Log out/in once for docker + plugdev + kvm group changes.
tools/bootstrap/install-go.sh
tools/bootstrap/install-android-sdk.sh
source "$HOME/.config/nodehost/env.sh"
yes | sdkmanager --licenses
```

Authorize one ARM64 Android phone with ADB, then:

```sh
make doctor
make device-facts
```

## Human: initialize laboratory state

```sh
cp lab/headscale/.env.example lab/headscale/.env
# Edit HEADSCALE_PUBLIC_URL to the development host's LAN URL.
make lab-up
make lab-keys
make lab-status
```

Confirm the phone can open the Headscale health URL. Live keys remain in ignored
files under `lab/headscale/secrets/`.

## Human or preparatory agent: import the pinned upstream

```sh
make import-podroid
make wire-podroid
make install-hooks
make validate
```

Run the unmodified Podroid build/boot baseline before broad adaptation whenever
possible:

```sh
cd android/podroid
./gradlew :app:testDebugUnitTest :app:assembleDebug
```

## Start the overnight orchestration

```sh
make integration-worktree
make wave WAVE=1
make goal-preflight
```

Give the orchestrator:

```text
GOAL.md
AGENTS.md
agents/overnight-goal.md
agents/task-dag.json
```

It should generate each task's scoped context with `make context TASK=Txx`, use
one worktree per packet, commit with exact provenance trailers, and integrate
with `make integrate TASK=Txx` in DAG order.

## Expected authorization boundaries

The overnight runner may use:

- the repository and `.worktrees/`;
- the already authorized Docker/Podman socket;
- the already authorized ADB device;
- the installed Android SDK/NDK;
- ignored laboratory auth-key files required by its assigned task.

Do not give it root credentials, production Headscale API keys, APK signing
keys, or unrelated SSH/private keys.

## Completion evidence

A valid report includes:

- integrated commit SHAs and agent trailers;
- exact commands/tests run;
- acceptance-ledger changes with evidence paths;
- physical/VPN checks marked `PASS` or `BLOCKED-HARDWARE`;
- remaining scoped `TODO(MVP-HARDENING, Txx)` items;
- the smallest next action for each blocker.

USB networking remains unscheduled until every B-item in
`docs/roadmap/acceptance-ledger.md` is `PASS`.

## Reconstructing from the downloadable bundle

The release helper produces a source tarball, a Git bundle, and checksums. For
the agent workflow, prefer the bundle because it preserves the initial commit
and provenance trailers:

```sh
sha256sum -c nodehost-mvp-scaffold.SHA256SUMS
git clone nodehost-mvp-scaffold.git.bundle nodehost-mvp-scaffold
cd nodehost-mvp-scaffold
make validate
```
