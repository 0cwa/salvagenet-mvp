# ADR-012 — Static public site, theme-aware design system, and roadmap truth

Status: Accepted

## Context

SalvageNet needs a public website that explains the project honestly, remains useful without JavaScript, reflects current acceptance evidence, and can be maintained by agents without creating another drifting project plan.

The repository already separates three kinds of state:

1. `GOAL.md` and architecture decisions define durable project direction;
2. `agents/task-dag.json` and task packets define current implementation authorization;
3. the acceptance ledger and evidence records define which product claims are validated.

A public GitHub issue roadmap adds a fourth concern: planned outcomes and their dependencies. It must not replace any of the existing authorities.

## Decision

### Static site

The public site at `salvage.network` will be a statically generated Astro site in this repository under `website/`.

- The production artifact is static HTML, CSS, JavaScript, images, and generated JSON.
- No application server is required for normal page delivery.
- Public content remains readable and navigable when JavaScript is unavailable.
- GitHub, acceptance, release, and device data are fetched or generated at build time, never from the visitor's browser.
- The exact built `dist/` artifact that passes validation is the artifact that is deployed.

### Component and CSS system

The site uses reusable Astro components and one site-wide, token-driven CSS design system.

- Source CSS is separated into reset, tokens, base, typography, layout, component, utility, motion, and print layers.
- Those sources compile into one hashed site stylesheet.
- Brand colours, spacing, type scales, radii, motion durations, and semantic states are design tokens.
- Components use semantic variants and must not invent page-local brand values.
- Status must never be communicated by colour alone.

### Light and dark themes

The default theme follows the visitor's browser or operating-system preference.

- With no saved override, CSS uses `prefers-color-scheme` and `color-scheme: light dark`.
- A visible, keyboard-accessible theme control offers **System**, **Light**, and **Dark**.
- A chosen override is stored locally under `salvagenet.theme`; no account or server storage is involved.
- A tiny inline head script may apply the saved override before first paint to avoid a theme flash.
- Selecting **System** removes the override and resumes following browser changes.
- Both themes use the same semantic tokens, information hierarchy, and component APIs.
- Motion respects `prefers-reduced-motion` independently of theme.

### Progressive enhancement

JavaScript is optional and component-scoped.

Acceptable enhancements include roadmap filtering, dependency highlighting, local guide search, a local setup checklist, local APK checksum verification, evidence disclosures, and restrained circuit-line motion.

Every enhancement must preserve a complete accessible HTML baseline and must not make a false freshness claim.

### Roadmap truth

Public roadmap state is represented by GitHub Issues, milestones, and issue dependency links.

The authorities remain distinct:

| Concern | Authority |
|---|---|
| Durable project direction | `GOAL.md` and accepted ADRs |
| Planned outcomes and dependencies | GitHub roadmap issues and milestones |
| Current agent work authorization | `agents/task-dag.json` and the active task packet |
| Validated product claims | acceptance ledger and reviewed evidence |
| Website data | generated, schema-versioned snapshots of the authorities above |

Closing an implementation issue does not close an acceptance gate. A future roadmap issue is not work authorization merely because it exists.

### Roadmap snapshots

The site generator writes a compact, schema-versioned, last-known-good roadmap snapshot and a smaller agent index.

- Network failures may fall back to a recent complete snapshot.
- Structural errors such as missing milestones, dependency cycles, invalid task paths, or unknown schema versions fail the build.
- Partial dependency data is never published.
- The snapshot contains summaries and links, not full issue bodies, comments, logs, or review threads.
- The public page shows the generated time, source hash, and whether fallback data was used.

## Consequences

- The website cannot hard-code current gate counts, candidate identities, roadmap status, or active work.
- A theme change does not require alternate page templates or duplicated component styles.
- Website interactivity remains small, replaceable, and testable in isolation.
- Roadmap issues may be split, merged, reordered, deferred, or removed at phase boundaries while durable goals and acceptance coverage remain intact.
- A roadmap generator and bootstrap process are required before the issue tracker becomes the roadmap authority.
- The existing acceptance and agent-task systems remain authoritative for their own concerns.

## Reconsideration triggers

Revisit this decision only if:

- a required public feature cannot be produced safely as a static artifact;
- static build times become operationally unacceptable after measured optimisation;
- a second independently deployed site proves that same-repository ownership causes more drift than it prevents;
- or accessibility testing shows that the selected interaction model needs a different implementation.
