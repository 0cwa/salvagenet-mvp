# SalvageNet public website

This directory will contain the static public site for `salvage.network`.

## Planned stack

- Astro with static output;
- reusable `.astro` components;
- one token-driven global CSS design system;
- schema-checked content collections for repeated content;
- small progressively enhanced TypeScript components;
- build-time project data from repository truth;
- exact-artifact deployment through GitHub Actions.

The implementation task begins only after ADR-012 and the roadmap-governance contract are accepted.

## Public pages

```text
/
/how-it-works
/get-started
/use-cases
/devices
/downloads
/guides
/security
/community
/status
/roadmap
/about
/help
```

A developer subsection is deliberately deferred. The repository remains the technical source until that subsection is planned.

## CSS architecture

Source CSS will be split for ownership but compiled into one hashed site stylesheet:

```text
src/styles/
├── index.css
├── reset.css
├── tokens.css
├── base.css
├── typography.css
├── layout.css
├── components.css
├── utilities.css
├── motion.css
└── print.css
```

`index.css` defines cascade-layer order and imports the files above.

Components consume semantic tokens. Raw brand values belong only in `tokens.css`.

## Theme behaviour

The first implementation must support three states:

```text
System   default; follows browser/OS preference
Light    saved local override
Dark     saved local override
```

The theme control must be keyboard accessible and labelled. The saved override uses `localStorage` key `salvagenet.theme`. Selecting **System** removes the key.

A tiny inline script in the document head may set `data-theme` before CSS paint. No other site content may depend on that script.

## Progressive enhancement

Useful enhancements may include:

- roadmap filtering and dependency highlighting;
- local guide and FAQ search;
- a local setup checklist;
- local APK SHA-256 comparison;
- evidence disclosures;
- restrained circuit-line motion;
- responsive roadmap layout.

Static HTML remains complete when JavaScript is unavailable.

## Data boundaries

```text
GitHub issues/milestones/dependencies
    → planned roadmap outcomes

agents/task-dag.json + active packet
    → current work authorization

acceptance ledger + evidence
    → validated project claims

generated website snapshots
    → static publication cache
```

The site must never infer a passed acceptance gate from a closed implementation issue.

## Expected implementation order

1. design tokens, global CSS, page shell, header/footer, theme control, and component gallery;
2. user-facing pages and content;
3. generated acceptance/release status;
4. issue-roadmap fetch, validation, snapshots, and agent index;
5. progressive enhancements;
6. exact-artifact deployment and freshness automation.

## Design review route

The foundation should include a preview-only component gallery at `/__design/` containing:

- light and dark tokens;
- typography;
- buttons and links;
- cards and layout primitives;
- status chips;
- forms and theme control;
- safety and error callouts;
- roadmap nodes and milestones;
- empty, stale, loading-enhancement, and failure states;
- reduced-motion examples.

It should be excluded from the production sitemap and navigation while remaining available in preview builds and visual regression tests.
