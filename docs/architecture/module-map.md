# Module map

## Android workspace

```text
android/podroid/                 imported upstream fork; composition host
android/modules/node-model/      domain value types and state machines
android/modules/node-core/       use cases, reconciler, ports, events
android/modules/node-store/      Room operation/current-state adapter
android/modules/runtime-qemu/    Podroid-derived QEMU adapter and command compiler
android/modules/mesh-tailscale/  Android-aware libtailscale adapter
android/modules/control-api/     typed Host API adapter
android/modules/node-shell/      Android service, receivers, composition root
android/modules/test-support/    fakes and contract harnesses
```

## Dependency direction

```text
node-model
    ^
    |
node-core
    ^
    +------------------+------------------+-------------------+
    |                  |                  |                   |
node-store       runtime-qemu       mesh-tailscale       control-api
    ^                  ^                  ^                   ^
    +------------------+------------------+-------------------+
                               |
                           node-shell
                               |
                         Podroid app hook
```

`control-api` depends on `node-core` use cases, not on QEMU or Room implementations. `node-shell` is the only module that constructs concrete adapters together.

## Monolithic module roots

Each module owns its implementation, tests, local README, and nearest `AGENTS.md`. Cross-module source directories are forbidden. New modules require a dependency-direction entry and a task packet.

## Podroid modification policy

Prefer sibling modules. Permitted Podroid changes for the MVP:

1. include sibling Gradle modules;
2. add one dependency on `:node-shell`;
3. add a narrow navigation/setup entry point if needed;
4. move or wrap QEMU classes only in the assigned extraction task;
5. preserve upstream history and record copied/moved file provenance.

Do not scatter new node-host business logic throughout Podroid UI, DataStore repositories, or guest product code.

## Non-Android roots

```text
profiles/          profile definitions and trusted bootstrap assets
control/           schemas and OpenAPI contract
controller/mvp-cli temporary Python controller and ProxyCommand
lab/               disposable Headscale/QEMU test environments
hostd/             post-MVP Linux service placeholder
usb-link/          MVP+ design and skeleton; blocked in base DAG
agents/            scoped task packets and orchestration metadata
tools/             deterministic bootstrap, CI, context, and provenance tools
tests/             cross-module and physical-device harnesses
```
