# Initial scaffold validation

Validated on **2026-07-29** in the artifact-generation environment.

## Passed locally

`make validate` completed successfully and covered:

- AGENTS hierarchy and task-packet coverage;
- context-budget and context-reference checks;
- task-DAG cycle/dependency and parallel path-ownership checks;
- JSON schemas, examples, VM profiles, guest-init includes, and OpenAPI shape;
- onion dependency direction and release-surface restrictions;
- secret-pattern and scoped-TODO checks;
- shell syntax/lint fallback checks;
- pure Kotlin domain/application compilation;
- Python unit tests and bytecode compilation;
- acceptance-evidence schema checks;
- enforcement that USB MVP+ is blocked while any base gate is not `PASS`;
- task-wave worktree creation, scoped context generation, and Git branch layout in a disposable clone;
- scoped task-branch verification, non-fast-forward integration, and full post-merge validation in a disposable clone.

## Environment audit

`make doctor` confirmed the basic repository tools and sufficient workspace
storage. This generation environment has JDK 21 and Go 1.23.2 active rather
than the scaffold's selected JDK 17 and Go 1.26.3. It also lacks Docker/Podman,
ADB, Android SDK tools, host QEMU, and an authorized physical device.

The user-local setup scripts now install/select JDK 17, Go 1.26.3, Android SDK
36, build tools 36.0.0, and NDK r27c on the intended development host.

## Deliberately not run here

The following require network access, root-authorized host services, imported
upstream source, or physical Android authorization and therefore remain
acceptance-ledger work rather than claimed passes:

- Podroid subtree import, Gradle build, native QEMU/kernel/rootfs build, or APK installation;
- Docker/Podman Headscale laboratory startup and pre-authentication-key creation;
- Linux host-QEMU Ubuntu/cloud-init boot laboratory;
- Android emulator installation or instrumentation tests;
- physical APK-native QEMU, 4/16 KiB native alignment, lifecycle, thermal, or OEM tests;
- Android `VpnService` permission and embedded libtailscale/Headscale enrollment;
- guest Tailscale enrollment, recovery SSH, and full controller-to-guest E2E;
- USB AOA/TAP networking, which is intentionally blocked until every B gate passes.

Use `HANDOFF.md` for the authorized-host sequence and
`docs/roadmap/acceptance-ledger.md` for evidence-bearing status updates.
