# NodeHost MVP development scaffold

This repository is the agent-first development workspace for turning a Podroid-derived Android application into a remotely managed node host.

The scaffold intentionally does **not** contain Podroid. Import the pinned upstream snapshot with:

```sh
make import-podroid
make wire-podroid
```

The base MVP is:

1. Preserve Podroid's APK-packaged QEMU launch model.
2. Replace the fixed Alpine appliance model with typed VM profiles and imported images.
3. Import a node-enrollment configuration that authorizes host and guest Headscale/Tailscale identities plus controller/SSH access.
4. Deploy, start, stop, reset, and remove one QEMU VM through a typed host API.
5. Reach and provision the guest through ordinary SSH after it joins Headscale.

USB networking is explicitly **MVP+** and starts only after the base MVP acceptance suite is green.

## Start here

```sh
cat GOAL.md
cat AGENTS.md
make doctor
make validate
```

Complete [`HANDOFF.md`](HANDOFF.md), then use [`agents/overnight-goal.md`](agents/overnight-goal.md) for the overnight goal-mode run. The orchestrator should dispatch the task packets under [`agents/tasks/`](agents/tasks/) rather than loading the full documentation tree.

## Canonical map

| Need | Read |
|---|---|
| Product result and success conditions | `GOAL.md` |
| Human authorization and overnight launch | `HANDOFF.md` |
| Generated repository map | `SCAFFOLD-MANIFEST.md` |
| Initial validation and unrun hardware gates | `VALIDATION.md` |
| Architecture and boundaries | `docs/architecture/overview.md` |
| Core/adopted/hack/test classification | `docs/architecture/classification.md` |
| Module ownership | `docs/architecture/module-map.md` |
| Overnight task order | `docs/roadmap/overnight-plan.md` |
| Host authorization/setup | `docs/development/root-authorization-checklist.md` |
| Test strategy | `docs/testing/strategy.md` |
| Research evidence | `docs/research/source-register.md` |

## Commands

```sh
make help
make doctor
make validate
make context TASK=T02
make lab-up
make lab-keys
make test-jvm             # after Podroid import/wiring
make device-facts         # with an authorized Android device
```

## Repository state

The initial scaffold is documentation, contracts, task packets, build fragments, module roots, test harnesses, and small compilable/reference stubs. The first overnight task imports Podroid at `android/podroid/` and wires these sibling modules into its Gradle build.

## Handoff packaging

After the repository is clean, `make package` creates both a source archive and
a Git bundle. Clone the bundle to preserve the scaffold commit and provenance:

```sh
git clone nodehost-mvp-scaffold.git.bundle nodehost-mvp-scaffold
cd nodehost-mvp-scaffold
make validate
```
