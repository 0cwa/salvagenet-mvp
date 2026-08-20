# Website roadmap integration handoff

Status: implementation handoff for the parallel public-site workstream

This document gives a website designer or frontend implementation agent the
technical contract needed to integrate SalvageNet's roadmap without coupling
the site to MVP runtime development.

The roadmap is one public component of the site. It is **not** the site itself,
it is not a project-management UI, and it must never become a prerequisite for
Android, guest, controller, or physical-device development.

## Product boundary

Website work may proceed in parallel with MVP implementation and validation.
The website consumes reviewed repository outputs and communicates them; it does
not authorize work, mutate GitHub, run the node controller, or decide whether a
product claim is validated.

The public site should explain the project in ordinary language:

> SalvageNet is an open-source platform for turning spare or retired Android
> devices, computers, and single-board computers into secure, remotely
> manageable self-hosting nodes. The Android app provisions and supervises
> Linux execution environments, connects them to a private network, and exposes
> a narrow authenticated management interface while established tools manage
> workloads in their native formats.

The supplied visual concepts are design references only. Their copy, diagrams,
statistics, product names, and capability claims are not technical authority.

## Current repository state

There is not yet an Astro application or JavaScript package manifest under
`website/`. The repository already contains the contracts that the future site
will consume:

| Concern | Current source |
|---|---|
| Site architecture and pages | `website/README.md` |
| Website implementation constraints | `website/AGENTS.md` |
| Roadmap architecture decision | `docs/architecture/decisions/ADR-012-static-site-and-roadmap-truth.md` |
| Generated public roadmap input | `website/data/roadmap.snapshot.v1.json` |
| Snapshot generator | `tools/roadmap/sync.py` and `tools/roadmap/roadmap.py` |
| Planned outcomes and dependencies | GitHub roadmap issues and milestones |
| Current development authorization | `agents/task-dag.json` and the active task packet |
| Validated product claims | `docs/roadmap/acceptance-ledger.md` and reviewed evidence |

The frontend should import the committed snapshot at build time. It should not
call GitHub from a visitor's browser and should not maintain a handwritten copy
of roadmap state.

## Authority boundaries

The site must keep these state channels separate:

| Displayed concept | Authority | What it means |
|---|---|---|
| Project direction | `GOAL.md` and accepted ADRs | Durable intent and architecture |
| Roadmap outcome | GitHub issue and milestone graph | Planned work and ordering |
| Work status | Issue workflow labels, projected into the snapshot | Planning/development state |
| Current agent task | `agents/task-dag.json` | Internal implementation authorization |
| Validation status | Acceptance ledger and evidence | What has actually been proven |
| Website data | Generated snapshot | A publication cache of the authorities above |

Important consequences:

- `workState: "done"` means the roadmap outcome's issue is closed. It does not
  mean every related acceptance gate passed.
- `acceptance[].status` must never be inferred from issue state, pull requests,
  milestone progress, or design copy.
- `dependencyState: "blocked"` means at least one declared blocker issue is
  still open. It does not mean the work failed.
- `taskAuthorized` is an internal agent-coordination fact. The public UI should
  normally express the corresponding `active` item as **In development** rather
  than exposing authorization language.
- Pull-request state is useful supporting detail, not a validation claim.

## Snapshot contract

The publication input is:

```text
website/data/roadmap.snapshot.v1.json
```

A machine-readable companion contract is kept at:

```text
website/schemas/roadmap.snapshot.v1.schema.json
```

### Top-level fields

| Field | Meaning |
|---|---|
| `schemaVersion` | Contract version. The current value is `1`. Unknown versions fail the build. |
| `generatedAt` | UTC time at which the projection was generated. |
| `source` | Repository, source hash, newest issue update, and fallback metadata. |
| `milestones` | Ordered milestone metadata. |
| `items` | Complete roadmap item projection. |
| `disagreements` | Structural/workflow contradictions detected during projection. |

A production build should reject a snapshot when:

- `schemaVersion` is unsupported;
- required fields fail schema validation;
- `disagreements` is non-empty;
- dependencies reference an unknown item;
- duplicate item IDs or milestone numbers exist;
- a public item references an unknown milestone;
- a normal deployment is asked to publish data older than the reviewed
  freshness policy.

### Source and freshness fields

Normal live projection:

```json
{
  "repository": "0cwa/salvagenet-mvp",
  "sourceHash": "sha256:…",
  "newestIssueUpdate": "2026-07-31T02:30:01Z",
  "fallback": false
}
```

A transient transport failure may use a recent complete snapshot and add:

```json
{
  "fallback": true,
  "fallbackReason": "bounded diagnostic text",
  "snapshotAgeSeconds": 1234
}
```

The current generator permits fallback only when the last-known-good snapshot
is no more than 72 hours old. Structural errors never use fallback.

The page should always expose a quiet freshness line containing:

- human-readable generated time;
- newest issue update time when present;
- shortened source hash with an accessible full value;
- a visible **Cached snapshot** warning when `fallback` is true.

Do not present fallback data as live. Do not show raw `fallbackReason` to the
public unless it has been explicitly reviewed for publication; it is primarily
a build diagnostic.

### Item fields

Each item currently projects:

```ts
interface RoadmapItem {
  id: string;
  number: number;
  title: string;
  summary: string;
  url: string;
  milestone: string;
  area: string;
  kind: string;
  public: boolean;
  workState: "done" | "review" | "active" | "ready" | "queued" | "hold" | "planned";
  dependencyState: "clear" | "blocked";
  blockedBy: string[];
  taskPacket: string | null;
  taskAuthorized: boolean;
  acceptance: Array<{ id: string; status: string }>;
  updatedAt: string | null;
  pullRequests: RoadmapPullRequest[];
}
```

Only render `public: true` items on the public site. Internal items still remain
in the complete dependency graph so build-time validation can prove that the
published projection is not structurally misleading. Do not leak internal item
content into HTML, client JavaScript, search indexes, or generated JSON.

### Work-state display language

Recommended public labels:

| Snapshot value | Public label | Meaning |
|---|---|---|
| `active` | In development | Current implementation work |
| `review` | Under review | A proposed implementation is being reviewed |
| `ready` | Ready next | Unblocked candidate work, not a promise of immediate delivery |
| `queued` or `planned` | Planned | Present in the roadmap but not current work |
| `hold` | Later / on hold | Intentionally deferred or awaiting a phase decision |
| `done` | Implementation complete | Issue outcome closed; validation may still be pending |

`dependencyState` should be shown separately. For example, a queued card may
say **Waiting on GUEST-01** rather than replacing its work state with a generic
"blocked" badge.

### Acceptance display language

Acceptance statuses are evidence state, not roadmap progress. At minimum, the
UI must support arbitrary uppercase ledger states while giving reviewed labels
to the currently used values:

| Ledger status | Suggested public label |
|---|---|
| `PASS` | Verified |
| `BLOCKED-HARDWARE` | Awaiting physical validation |
| `DEFERRED` | Deferred |

An item with `workState: "done"` and an unverified acceptance gate should read
**Implementation complete; physical validation pending**, not **Complete**.
Avoid percentage-complete calculations: roadmap outcomes and acceptance gates
are not equal-sized units.

## Recommended Astro integration

Keep parsing and derived views outside page components:

```text
website/src/
├── data/roadmap.ts              # load, validate, normalize, derive maps
├── components/roadmap/
│   ├── RoadmapFreshness.astro
│   ├── RoadmapLegend.astro
│   ├── RoadmapMilestone.astro
│   ├── RoadmapItemCard.astro
│   ├── RoadmapDependencies.astro
│   ├── RoadmapAcceptance.astro
│   └── RoadmapFilters.ts         # optional progressive enhancement
└── pages/roadmap/
    ├── index.astro
    └── [id].astro                # optional static detail pages
```

Suggested build-time flow:

1. Import `website/data/roadmap.snapshot.v1.json`.
2. Validate it against the versioned schema before rendering.
3. Reject non-empty `disagreements`.
4. Construct `itemById` and `milestoneByTitle` maps.
5. Validate every blocker and milestone reference.
6. Filter public output only after complete-graph validation.
7. Derive view models; do not mutate the imported snapshot.
8. Render complete static HTML.
9. Hydrate only the optional filtering/highlighting component.

Astro already uses Zod in its content tooling, so a small Zod parser generated
from or kept equivalent to the JSON Schema is reasonable. The JSON Schema
remains the framework-independent contract.

## Roadmap information architecture

The primary roadmap should be a readable milestone journey, not a 53-node
free-form graph.

Recommended baseline:

1. **Where we are now** — one active/review card and a short evidence-aware
   project-status statement.
2. **Milestone route** — ordered milestone sections containing compact cards.
3. **Item detail** — title, plain-language outcome, work status, validation
   status, dependencies, and links to the public GitHub issue or PRs.
4. **How to read this roadmap** — explain the difference between implementation,
   dependencies, and validation.
5. **Freshness/provenance** — generated time and source hash.

The decorative circuit/route language in the supplied design concepts is a
strong visual metaphor for milestones and dependencies. It must not be the only
way relationships are communicated. Every dependency line needs an equivalent
text list or link.

### Responsive behaviour

- At narrow widths, use a single chronological milestone column.
- Cards should remain normal document flow; do not require horizontal dragging
  to read the roadmap.
- Optional dependency highlighting may scroll or focus related cards, but must
  not move focus unexpectedly.
- A wide-screen route or dependency view may use SVG, provided the equivalent
  HTML structure remains present and accessible.
- Do not use a canvas-only graph.

## Progressive enhancement contract

All roadmap items, milestones, status text, and freshness information must be
present without JavaScript.

Optional enhancement may provide:

- filters by milestone, area, kind, and work state;
- a text search over already-rendered public items;
- dependency highlighting;
- compact/expanded card preference;
- shareable query parameters or anchors;
- restrained route-line motion when reduced motion is not requested.

Implementation rules:

- use semantic buttons, inputs, and links;
- preserve stable anchors such as `/roadmap/#GUEST-01`;
- keep filter state local; no account or remote persistence;
- ensure browser back/forward behaviour remains intelligible;
- do not hide the only copy of content behind disclosure widgets;
- respect `prefers-reduced-motion`;
- never fetch GitHub in browser JavaScript.

## Visual mapping for roadmap components

Use the design boards as a visual vocabulary, not a source of product truth.

Recommended mapping:

- warm cream/canvas background for the roadmap page;
- dark teal ink and borders for primary structure;
- moss green for verified/complete states;
- amber for ready/current-route emphasis;
- copper/orange for warnings, deferred work, or important junctions;
- teal signal accents for interactive focus and selected filters;
- circuit paths and nodes as restrained section framing;
- generous whitespace and readable cards rather than a dense engineering
  dashboard.

Status must always pair icon/shape and text with colour. Decorative circuit
lines must remain behind content, avoid intersections with body text, and
simplify or disappear under reduced motion or narrow layouts.

Do not copy these inaccurate or unsupported patterns from concept art:

- a product named **SalvageOS**;
- invented user counts, adoption figures, release dates, or progress
  percentages;
- claims of broad device compatibility before device evidence exists;
- claims that every workload is encrypted end to end by SalvageNet itself;
- claims of production readiness or unattended reliability;
- diagrams that imply the website/browser directly controls nodes;
- generic cloud-service dashboards unrelated to the static public site.

## Performance and accessibility budget

Initial targets for the roadmap route:

- static HTML is the complete experience;
- zero hydrated components by default, one small filter component when enabled;
- no graph-layout framework in the foundation;
- no client-side GitHub SDK;
- no remote font required for first implementation;
- all icons are inline SVG or an audited local sprite;
- normal text meets WCAG AA contrast in light and dark themes;
- focus is visible without relying on colour alone;
- print output shows item IDs, status text, dependencies, and freshness while
  omitting decorative route lines.

The eventual task packet may set stricter numeric JavaScript or image budgets.
Do not loosen repository-wide CI to accommodate the website.

## Test matrix

The implementing agent should add focused website checks rather than running
unrelated Android/device qualification as a prerequisite for every design
iteration.

Required foundation checks:

- JSON Schema validation using representative normal and fallback fixtures;
- unsupported schema version fails;
- non-empty disagreements fail;
- unknown blocker or milestone fails;
- internal items do not appear in built HTML or browser bundles;
- normal and fallback freshness states render correctly;
- no-JavaScript roadmap contains all public information;
- keyboard-only filtering and dependency navigation;
- touch target and narrow-layout checks;
- light, dark, and System theme screenshots;
- reduced-motion behaviour;
- automated accessibility scan;
- broken-link check for generated GitHub URLs;
- production build contains no browser request to GitHub APIs.

Run full repository checks at integration boundaries, but keep the website's
fast local test loop independent so it can progress in parallel with the MVP.

## Update and deployment flow

```text
GitHub issues, milestones, dependencies
        │
        ▼
tools/roadmap/sync.py
        │  validates full graph, acceptance metadata and task alignment
        ▼
website/data/roadmap.snapshot.v1.json
        │  committed/reviewed publication cache
        ▼
Astro build-time parser and components
        │
        ▼
validated static dist artifact
        │
        ▼
exact-artifact deployment
```

A site build may consume the reviewed committed snapshot. A scheduled or
maintainer-triggered refresh may update it through a normal PR. The website
must not block MVP code changes merely because the roadmap has not changed.
Conversely, the website deployment workflow should refuse to claim live
freshness when the snapshot is stale or a fallback.

## Deliberately unresolved implementation choices

The design/foundation agent may decide these inside WEB-01/WEB-05 while keeping
the contract above:

- whether item details use static subpages, anchored cards, or both;
- whether the enhanced wide-screen dependency view uses SVG or DOM/CSS lines;
- whether filters use URL query parameters or local component state;
- the exact breakpoint and card density;
- the final local font files or system-font fallback;
- the exact stale-warning wording.

These choices do not require changes to the snapshot generator.
