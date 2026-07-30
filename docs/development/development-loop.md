# Development loop

## Fast local loop

```sh
make dev-plan
make dev-check
```

`dev-plan` reports which checks the current host can execute. `dev-check` runs repository validation and guest/profile tests, writes a machine-readable report under `.local/development/`, and fails on a failed check while treating unavailable optional environments as `SKIP`.

## Full non-hardware loop

```sh
make dev-full
```

When Gradle and the Android SDK are available, this adds JVM/domain and Android adapter/lint tests. Add `DEV_WITH_QEMU=1` to run the one-command host-QEMU laboratory.

## Agent task loop

```sh
make status
make integration-worktree
make wave WAVE=1
make context TASK=H01
python3 tools/agents/verify-scope.py H01
make integrate TASK=H01
```

The task graph represents the active cycle only. Completed packets remain in Git for provenance but do not drive new work.

## Adding a task

Use the checked generator instead of hand-editing four packet files and two JSON manifests:

```sh
python3 tools/agents/new-task.py --id H05 --slug profile-registry   --name 'JSON-backed production profile registry' --group 2   --depends-on H02 --allowed-path 'profiles/**'   --context docs/architecture/vm-profiles.md \
  --acceptance 'Packaged JSON is the production source of truth.' --write
```

The generator defaults to a dry-run, validates IDs, dependencies, paths and context count, and writes atomically only with `--write`.
