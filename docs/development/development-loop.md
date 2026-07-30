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

`agents/task-dag.json` contains only the active phase; merged, superseded, and queued packets remain in `agents/task-registry.json`.

Before current implementation:

```sh
git pull --ff-only
make dev-plan
make validate
make status
make context TASK=WEB04
```

Then:

1. verify the phase entry criteria in `agents/task-dag.json`;
2. compare the task with `GOAL.md`, `docs/roadmap/podroid-mvp-alignment.md`, current roadmap/PR/acceptance/debt state, and current implementation;
3. revise or stop if prerequisites, scope, compatibility policy, or acceptance criteria are no longer accurate;
4. create only the active task worktree/branch.

Completed, superseded, paused, or queued packets are not work authorization merely because they exist under `agents/tasks/` or GitHub Issues.

## Task loop

For the current phase:

```sh
make worktree TASK=WEB04
make context TASK=WEB04
# run the smallest relevant checks while implementing
python3 tools/agents/verify-scope.py WEB04
```

Open a focused PR against `main`. Update the active issue, packet, and experiment record in the same branch when implementation discovery changes the true remaining work. Large roadmap reshaping belongs in a phase-transition PR.

## Phase-end loop

### Before merge-ready

1. check every task acceptance criterion;
2. check every phase exit criterion;
3. run packet-local checks and full applicable CI;
4. inspect artifacts, live graph, or evidence where the criteria require them;
5. record unavailable hardware or external checks;
6. record the exact tested head and resolve or disposition review findings;
7. mark review/merge-ready state without closing the issue or claiming merge.

### After approval and merge

1. merge the exact tested and reviewed head;
2. update registry, roadmap issue, experiment, and evidence references with the merge SHA where applicable;
3. close the issue only when its implementation outcome is complete;
4. leave acceptance gates unchanged unless their own required evidence passed;
5. refresh current `main`, roadmap, PR, debt, and acceptance state;
6. re-evaluate queued tasks before creating the next active DAG.

Do not pre-create a multi-task wave solely to maximize parallelism. Parallel tasks are appropriate only after prerequisites are true, write paths are disjoint, and the phase remains understandable to a human reviewer.

## Adding a task

Use the checked generator only after a phase-boundary review has approved the task. The generated packet is a starting point and must be expanded with status, phase-start review, compatibility policy, acceptance, verification, and phase-end review before activation.

```sh
python3 tools/agents/new-task.py --id F02 --slug example-foundation \
  --name 'Example foundation' --group 1 \
  --allowed-path 'path/**' \
  --context docs/architecture/overview.md \
  --acceptance 'One concrete, observable result.'
```

The generator defaults to a dry-run, validates IDs, dependencies, paths and context count, and writes atomically only with `--write`.
