# SalvageNet Website — Minimal Rebuild

Rebuild the SalvageNet public website as a small, visual Astro site. Delete the current presentation layer and start again.

This is **not** a documentation portal, engineering dashboard, acceptance-ledger viewer, or issue tracker. It should explain the project in under a minute and look unmistakably like the supplied SalvageNet designs.

## Visual source of truth

Open these before coding:

```text
/var/home/kyvernitria/Applications/salvagenet/salvagenet-website-design-handoff/visual/original/webdesign-final.png
/var/home/kyvernitria/Applications/salvagenet/salvagenet-website-design-handoff/visual/original/salvage-design-final.png
/var/home/kyvernitria/Applications/salvagenet/salvagenet-website-design-handoff/visual/original/official-logo-light.png
/var/home/kyvernitria/Applications/salvagenet/salvagenet-website-design-handoff/visual/original/official-logo-dark.png
```

These are not loose inspiration:

- `webdesign-final.png` is the homepage layout blueprint.
- `salvage-design-final.png` defines color, typography, lines, icons, and illustration style.
- The logo boards define the logo.
- Use clean optimized crops/exports from the supplied images. Do not replace the hero art with a homemade technical SVG.
- Export one light logo lockup and the hero device/network illustration from `webdesign-final.png`.
- Do not display an entire board or copy unsupported text from it.

Until canonical vectors exist, approved raster exports are preferred over an inconsistent redraw.

## Exact visual direction

The site supports paired light and dark themes. Light remains the default visual reference; dark uses a deep-teal canvas derived from the approved dark logo board.

```text
light canvas  #F7F4EE
dark canvas   #02232B
surface       #E6F0EC
ink/teal      #0C4B4F
moss          #6B8A72
amber         #FAC145
copper        #FF684A
signal teal   #2283A9
```

Cream must dominate. Dark teal is used for text, borders, and buttons. Moss softens the system. Amber and copper are small highlights.

No purple, SaaS gradients, glass, neon, black-background homepage, dashboard styling, giant shadows, or excessive rounded cards.

Use the board’s warm paper, outlined device art, circuit routes, small junctions, leaves, and pixel details. Keep decoration restrained.

## Content and information hierarchy

Lead with **why**: useful hardware can have another practical life. The first screen must be eye-catching, immediately understandable, and focused on the end-user possibility rather than implementation detail.

Use progressive disclosure:

1. top-level pages communicate one clear idea at a glance;
2. short supporting copy explains how it helps;
3. Status and Roadmap provide the next layer of detail;
4. gate-level engineering, evidence, and issue planning stay in the repository.

Prefer concise headings, visual structure, and scannable groups over long paragraphs. Accuracy remains mandatory, but cautionary implementation detail should not dominate the top-level story.

## Product truth

Verify public copy against:

```text
/home/kyvernitria/Applications/salvagenet-mvp/README.md
/home/kyvernitria/Applications/salvagenet-mvp/GOAL.md
/home/kyvernitria/Applications/salvagenet-mvp/docs/STATUS.md
/home/kyvernitria/Applications/salvagenet-mvp/website/data/roadmap.snapshot.v1.json
```

Use this simple explanation:

> SalvageNet is an open-source project working toward turning spare devices into remotely manageable self-hosting nodes. It prepares and supervises Linux, connects it privately, and leaves workload management to established tools.

Current boundary:

> The software foundations are being built, but the complete physical-device path is not yet validated.

Do not publish broad compatibility, production readiness, public-download, arbitrary-image, one-click-setup, or unattended-reliability claims.

## Tiny site scope

Build only:

```text
/
/status
/roadmap
/about
```

Detailed engineering, evidence, security, guides, issues, and contribution material stay in the repository.

Header:

- approved logo;
- How it works;
- Status;
- Roadmap;
- About;
- GitHub.

Nothing else.

## Homepage

Follow the proportions and rhythm of `webdesign-final.png`.

### Hero

Headline:

**Turn spare devices into useful self-hosting nodes.**

Use no more than two supporting sentences. Mention physical validation quietly.

Actions:

- See how it works
- View project status

Use the actual approved hero illustration exported from `webdesign-final.png`.

### Principle row

- Make hardware useful
- Keep control local
- Connect privately
- Use familiar tools

### How it works

Three steps only:

1. Start with an eligible spare device.
2. SalvageNet prepares and supervises Linux.
3. Use established tools to manage workloads.

One sentence per step.

### Current status

One calm horizontal panel:

- software foundations exist;
- physical validation is still pending;
- one broad sentence about current work;
- links to Status and Roadmap.

No percentages, gate counts, tables, issue IDs, metadata, or status-chip collections.

### Why it matters

Three short ideas:

- extend the useful life of existing hardware;
- keep infrastructure understandable and locally controlled;
- work with established open-source tools rather than replacing them.

### Closing

**Follow the project as it is built in the open.**

Link to GitHub and Roadmap. Use a very small footer.

## Status

A plain-language page with only:

1. what exists now;
2. what still needs proof;
3. what is being worked on;
4. a link to the repository status document.

Use short paragraphs and at most five bullets per section. Do not reproduce the acceptance ledger.

## Roadmap

Make this broad and visual, never issue-by-issue.

Show one circuit/transit route with five stages:

1. **Foundation** — core host and software groundwork.
2. **Physical validation** — prove the complete path on real hardware.
3. **Early access** — reviewed downloads, setup, recovery, and initial device records.
4. **Reliability** — thermal, storage, network, lifecycle, and update confidence.
5. **Broader platforms** — later Android tiers, SBCs, Linux, and other hosts.

Each stage gets one sentence. Highlight the current stage. Link to GitHub for detailed planning.

Do not render issues, pull requests, task IDs, gate IDs, dependency lists, filters, status walls, source hashes, or a project-management feed.

## About

Explain, in under 500 words:

- useful hardware deserves another life;
- SalvageNet integrates existing tools;
- the project is open and built to be understood.

## Build rules

- Astro static output.
- A few shared components, not a design-system project.
- One token file and one global stylesheet.
- No framework islands, search, filters, content collections, design gallery, animation framework, or card library.
- JavaScript only for theme preference; the mobile menu remains CSS-only.
- Complete without JavaScript and follow the system theme when no preference is stored.
- Motion defaults to none.
- Modest radii, almost no shadows, readable text, semantic HTML.
- The desktop homepage should fit in roughly five or six viewport heights.

## Workflow

1. Delete the existing visual/component complexity.
2. Export the approved logo and hero art from the supplied boards.
3. Build the light homepage first, then apply the paired dark treatment.
4. Compare light/dark desktop and 390px screenshots directly with `webdesign-final.png`.
5. Get visual approval before building Status, Roadmap, and About.
6. Do not expand scope.

## Success

The result is successful when it:

- visibly uses the supplied design artwork;
- uses the cream/teal/moss/amber/copper palette;
- is immediately recognizable as SalvageNet;
- leads with why and explains the project quickly;
- keeps technical limits accessible without letting them overwhelm the top-level story;
- presents a five-stage direction instead of an issue tracker;
- feels warm, calm, distinctive, and dramatically simpler than the previous site.
