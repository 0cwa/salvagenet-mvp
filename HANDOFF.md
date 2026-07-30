# Roadmap-foundation and MVP handoff

The repository is a **software-qualified device-lab candidate**, not a validated MVP. Ten of twenty base gates still require physical or live-network evidence.

PR #19 merged at `b42c35ac17793fb1621baf19905a0eacea9b3521` and accepted the Podroid-MVP alignment, issue-roadmap governance, human-aware agent workflow, and static-site/theme architecture.

## Current execution order

1. Complete WEB04: reviewed seed, GitHub labels/milestones/issues/dependencies, last-known-good snapshot, compact agent index, bounded context, and visible state/freshness tooling.
2. At the WEB04 phase boundary, normally reactivate H02A and consider path-disjoint WEB01 website-foundation work in parallel.
3. Complete H02A guest-boot qualification before deciding whether H02B guest-mesh preflight is still valuable.
4. Use the one-phone HIL runner for APK-native QEMU, host mesh/API, remote Ubuntu deployment, guest identity/SSH, recovery, lifecycle, reboot, and controller-offline evidence.
5. Bind every base gate to one exact source commit and APK.
6. Start USB work only after every B01–B20 gate passes.

This ordering is deliberate. The roadmap/agent foundation prevents the website and agents from maintaining separate plans. It does not change the product critical path or acceptance state.

## Current authorization

```sh
cat GOAL.md
cat AGENTS.md
cat agents/task-dag.json
cat agents/tasks/WEB04/task.md
cat docs/roadmap/podroid-mvp-alignment.md
make context TASK=WEB04
make dev-plan
make validate
```

Only WEB04 is authorised after the transition PR merges. H02A is queued for reactivation and must not be implemented from its existing packet until a fresh phase-start review restores it to the DAG.

## WEB04 boundaries

WEB04 may change only its reviewed roadmap, agent-context, snapshot, workflow, test, and phase-status paths.

It must not:

- edit Android/QEMU/profile/runtime behaviour;
- implement public website pages or styling;
- change acceptance gates or evidence;
- turn issue labels into work authorization;
- infer product validation from issue or PR state;
- overwrite legitimate issue refinements after bootstrap;
- introduce USB, broader guest-image, controller-rewrite, or platform work.

## Live GitHub bootstrap

GitHub Issues are enabled.

The implementation must:

1. create and review the complete machine-readable seed;
2. run an idempotent local dry-run;
3. run a live dry-run against `0cwa/salvagenet-mvp`;
4. apply from the exact reviewed `main` source through a manual workflow with explicit minimal permissions;
5. rerun to prove non-destructive idempotency;
6. generate and review the bounded snapshot and agent index in a normal PR.

Administrative credentials, GitHub tokens, issue comments, and raw API payloads must not enter snapshots or agent context.

## Phase handoff rule

### Before merge-ready

1. Check every task and phase exit criterion.
2. Run required tests and complete CI.
3. Record exact seed/schema/source identity and live dry-run/apply results.
4. Review graph completeness, dependencies, snapshot bounds, fallback/staleness, and secret absence.
5. Resolve or disposition every actionable review finding.

### After merge

1. Record the exact merge SHA and live graph source hash.
2. Mark WEB04 merged without altering acceptance gates.
3. Refresh roadmap, pull requests, debt, and current `main`.
4. Re-review H02A against the live graph and any merged device-lab safety changes.
5. Authorize WEB01 alongside H02A only if paths are disjoint and parallel work remains understandable.

## Later H02A host preparation

H02A is a Linux host-QEMU qualification phase. It does not require a phone or Headscale.

```sh
sudo tools/bootstrap/ubuntu-root-setup.sh
# Log out/in once for docker + plugdev + kvm group changes where applicable.
tools/bootstrap/install-go.sh
tools/bootstrap/install-android-sdk.sh
source "$HOME/.config/nodehost/env.sh"

make context TASK=H02A
make dev-plan
make validate
make qemu-lab-e2e
```

H02A evidence remains host-QEMU only and cannot close Android gates.

## Later physical preparation

Use one explicitly authorised ARM64 Android phone, exact ADB serial, reviewed APK identity, disposable Headscale state, and `tests/hil/` only.

```sh
cp lab/headscale/.env.example lab/headscale/.env
make lab-up
make lab-keys
make lab-status

cp tests/hil/config.example.json .local/hil.json
make hil-doctor HIL_BUILD=1
make hil-smoke HIL_BUILD=1
make hil-mvp
make hil-resilience
```

A fake, emulator, host-QEMU, package build, website, issue, or code review cannot close a physical gate. Never provide production Headscale credentials, release-signing keys, unrelated private keys, or general root access to an agent.
