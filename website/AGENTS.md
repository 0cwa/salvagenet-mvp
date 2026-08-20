# Public website instructions

## Product boundary

- The site is user- and community-facing. Keep developer internals in the repository until a dedicated developer section is explicitly planned.
- Public claims must match generated project status and reviewed evidence.
- Do not hard-code acceptance counts, active roadmap state, candidate identity, or device support.
- Do not imply stable, production-ready, broadly compatible, arbitrary-image, or unattended reliability support before the evidence permits it.

## Static-first rule

- Production output is static.
- Every page must remain readable and navigable without JavaScript.
- Do not call GitHub or other project APIs from the visitor's browser.
- Dynamic project data is fetched and validated at build time, then rendered into HTML and schema-versioned snapshots.
- Progressive enhancement may add filtering, local search, local file verification, local preferences, and restrained motion.

## Design system

- Use the shared tokens, global CSS layers, layout components, and section components.
- Do not introduce page-local brand colours, arbitrary spacing scales, or competing button/card systems.
- The visual direction is warm cream paper, dark teal ink and circuit lines, moss/leaf green, copper/orange, amber, and small teal signal accents.
- Avoid generic blue SaaS gradients, dark cyberpunk styling, fake dashboards, invented statistics, and decorative motion that obscures content.

## Themes

- Default to the visitor's browser or operating-system light/dark preference.
- Expose a visible, accessible **System / Light / Dark** control.
- Store only an explicit local override under `salvagenet.theme`.
- Selecting **System** removes the override and resumes following `prefers-color-scheme` changes.
- Apply the saved override before first paint to avoid a theme flash.
- Test both themes for contrast, focus, diagrams, status chips, code blocks, forms, and print.
- Respect `prefers-reduced-motion` separately from theme choice.

## Accessibility

- Use semantic HTML before ARIA.
- Status is never colour-only.
- Interactive enhancements require keyboard, touch, focus, reduced-motion, and no-JavaScript tests.
- Motion, disclosure, filters, and transitions must not trap focus or interfere with browser history.
- Safety warnings remain prominent in both themes and at narrow widths.

## Generated data

- GitHub issues and milestones define roadmap planning state.
- `agents/task-dag.json` defines current implementation authorization.
- The acceptance ledger and evidence define validated claims.
- Snapshots are caches and publication inputs, not independent authorities.
- A stale or fallback snapshot must identify its age and source hash.

## Verification

Before handoff, run the website checks defined by the active task packet. At minimum the foundation must cover:

- static build;
- no-JavaScript content;
- System, Light, and Dark theme behaviour;
- accessibility checks;
- broken links;
- generated-data schema validation;
- visual component examples;
- JavaScript budget for hydrated components.
