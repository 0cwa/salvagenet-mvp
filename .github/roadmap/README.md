# Roadmap bootstrap

GitHub Issues are enabled. WEB04 implements the reviewed one-time bootstrap and steady-state projections.

## Files

- `seed.v1.json` — reviewed bootstrap input; historical after live apply.
- `bootstrap-state.v1.json` — generated exact apply/source/issue map; created by the apply workflow and reviewed in a follow-up PR.
- `../workflows/roadmap-bootstrap.yml` — explicit dry-run/apply workflow.
- `../../tools/roadmap/roadmap.py` — validation, GitHub mutation, live graph, status, freshness, and bounded context.
- `../../tools/roadmap/sync.py` — live/seed projection with reviewed acceptance metadata.

## Local commands

```sh
make roadmap-validate
make roadmap-bootstrap-dry-run   # requires GH_TOKEN or GITHUB_TOKEN
make roadmap-sync               # live when token exists; reviewed fallback otherwise
make roadmap-status
make roadmap-check              # requires live token
make roadmap-context ISSUE=WEB-04
```

## Human-visible apply

After the implementation PR merges, open an issue with this exact title:

```text
[Roadmap Apply] Bootstrap reviewed graph
```

Then add one explicit comment containing the exact current default-branch commit:

```text
/roadmap-apply <40-character-main-sha>
```

The comment trigger avoids starting one workflow run for every roadmap issue created during bootstrap. The workflow verifies the comment author is a repository owner, member, or collaborator; verifies exact main; applies labels/milestones/issues/dependencies with `issues: write`; reruns without mutation; generates snapshots; and pushes a review branch. The generated state and caches enter `main` only through a normal follow-up PR.

A manual workflow dispatch offers the same dry-run/apply boundary.

## Truth after bootstrap

```text
GitHub Issues and dependencies     planned outcomes
agents/task-dag.json               current work authorization
acceptance ledger and evidence     validated product claims
website/agent snapshots            generated caches
```

Bootstrap is stable-ID-based and idempotent. After the generated state PR merges, reruns verify drift and do not overwrite issue bodies, state, dependencies, or planning notes legitimately refined by people or agents.

Issue-form submissions remain unclassified proposals until a maintainer adds the hidden stable marker, required metadata, milestone, area/kind/visibility labels, and `roadmap` label.
