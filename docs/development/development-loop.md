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

When Gradle and the Android SDK are available, this adds JVM/domain and Android adapter/lint tests. Add `DEV_WITH_QEMU=1` only when the current phase requires the host-QEMU laboratory.

## Phase-start loop

`agents/task-dag.json` contains only the active phase; merged and queued packets remain in `agents/task-registry.json`.

Before implementation:

```sh
git pull --ff-only
make dev-plan
make validate
make status
make context TASK=F01
```

Then:

1. verify the phase entry criteria in `agents/task-dag.json`;
2. re-read the active packet against current implementation;
3. revise or stop if prerequisites, scope, or acceptance criteria are no longer accurate;
4. create only the active task worktree/branch.

Completed or queued packets are not work authorization merely because they exist under `agents/tasks/`.

## Task loop

```sh
make worktree TASK=F01
make context TASK=F01
# run the smallest relevant checks while implementing
python3 tools/agents/verify-scope.py F01
```

Open a focused PR against `main`. Update the packet and experiment record in the same branch when implementation discovery changes the true remaining work.

## Phase-end loop

Before merge-ready status:

1. check every task acceptance criterion;
2. check every phase exit criterion;
3. run packet-local checks and full applicable CI;
4. inspect packaged artifacts where the criterion concerns runtime assets;
5. record checks unavailable without hardware;
6. merge the exact tested head;
7. update registry/roadmap status with the merge SHA;
8. re-evaluate queued tasks before creating the next active DAG.

Do not pre-create a multi-task wave solely to maximize parallelism. Parallel tasks are appropriate only after prerequisites are true and write paths are disjoint.

## Adding a task

Use the checked generator only after a phase-boundary review has approved the task. The generated packet is a starting point and must be expanded with status, phase-start review, acceptance, verification, and phase-end review before activation.

```sh
python3 tools/agents/new-task.py --id F02 --slug example-foundation \
  --name 'Example foundation' --group 1 \
  --allowed-path 'path/**' \
  --context docs/architecture/overview.md \
  --acceptance 'One concrete, observable result.'
```

The generator defaults to a dry-run, validates IDs, dependencies, paths and context count, and writes atomically only with `--write`.
