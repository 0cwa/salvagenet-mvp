# Android workspace instructions

- `android/podroid/` is imported upstream code. Prefer new implementation in `android/modules/`.
- The application is a modular monolith; modules are compile-time boundaries, not independently deployed services.
- `node-model` and `node-core` may not import Android or adapter packages.
- `node-shell` is the composition root and lifecycle owner.
- Preserve Podroid's QEMU executable packaging, launcher, dedicated spawn/reap thread, sockets, and diagnostics until replacement tests pass.
- No production path accepts raw QEMU/kernel arguments, raw QMP, or arbitrary shell.
- One active VM for base MVP.
- Do not add executable USB-link code until the base acceptance gate passes.
