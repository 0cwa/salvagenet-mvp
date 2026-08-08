# P01 — Model and reasoning provenance ledger

## Status

**PLANNED — active implementation authorization in the current foundation phase.**

## Outcome

Record and deterministically tabulate declared model/reasoning metadata plus exact Git commit scope in pull-request CI, without storing prompts, transcripts, or chain-of-thought.

## Prerequisites

None. This path-disjoint planning slice is authorized alongside WEB04; it does not authorize product/runtime, GitHub mutation, or release work.

## Phase-start review

Re-evaluate this packet against current `main`, the live roadmap/index, current pull requests, and the exact WEB04 result before merge-ready status. Confirm the slice remains path-disjoint and that no API, hook, attestation, or provider-specific dependency has entered the implementation.

## Compatibility policy

None. This repository is unreleased alpha; breaking internal changes and development-state reset are allowed. Do not add legacy readers or compatibility aliases. Any exception must identify real deployed state, explain why reset is unacceptable, isolate compatibility code from canonical paths, and name its deletion trigger.

## Allowed paths

See `allowed-paths.txt`. Changes outside them require an orchestrator handoff and phase-plan review. This slice must not add hooks, GitHub API clients, notes, databases, provider adapters, or product/runtime dependencies.

## Acceptance criteria

- New project-owned commits require the existing model, run, task, and mode trailers plus one `Agent-Reasoning` trailer; `unknown` and `not-applicable` are explicit values.
- A dependency-free report parses trailers deterministically over an exact Git range and never silently emits blank metadata.
- An isolated pull-request workflow validates the range and uploads a bounded, credential-free TSV/JSON artifact; it does not call the GitHub API or mutate pull requests.
- Existing history is not rewritten; validation enforces only the explicitly supplied Git range, so older commits remain readable without a compatibility reader.
- Focused tests cover missing metadata, repeated/multi-valued trailer handling, deterministic ordering, and exact base/head range selection.

## Required checks

```sh
make validate
python3 -m unittest discover -s tests/tools -p 'test_provenance*.py'
python3 tools/agents/verify-scope.py P01
```

## Phase-end verification

Check every acceptance criterion against code, tests, generated report fixtures, and CI evidence. Run the full applicable workflow on the exact head before merge-ready status, then re-evaluate the next phase from the actual result. Treat model and reasoning values as declarations; do not claim independent verification without a trusted provider/runtime evidence source.

## Handoff

Report commit SHA(s), tests, unavailable checks, ledger schema/version, exact base/head/merge mapping behavior, metadata coverage, evidence paths, concrete deferred items, every acceptance result, and the smallest next blocker.
