# Website design implementation brief

Status: visual and product handoff for the parallel public-site workstream

This brief translates the supplied SalvageNet design concepts into constraints
that a website design/implementation agent can safely build. It complements
`roadmap-integration.md`; neither document changes the MVP runtime roadmap or
blocks product testing.

## Supplied visual references

The project conversation contains these reference images:

### Strongest current direction

- `salvage-design-final.png` — primary design-system direction.
- `webdesign-final.png` — primary homepage and page-composition direction.
- `official-logo-light.png` — approved logo direction on a light presentation
  board.
- `official-logo-dark.png` — approved logo direction on a dark presentation
  board.

### Exploratory references

- `early-design-concept.png`
- `early-design-concept2.png`
- `very-early-design-concept.png`
- `early-webdesign1.png`
- `interesting-early-site-design-concept.png`

The final boards should win when references conflict. Exploratory boards remain
useful for illustration, pattern, editorial-density, and layout experiments.

These images are concept boards, not production image assets. The implementing
agent should create or request audited vector and responsive exports rather
than cropping presentation boards into the live site.

## Core visual direction

The strongest direction is **retro-futurism for real infrastructure**:
optimistic, welcoming, practical, open-source, and slightly rebellious without
turning into cyberpunk or nostalgic cosplay.

Use:

- warm cream/canvas page backgrounds;
- dark teal structural ink, typography, controls, and circuit paths;
- moss and leaf greens;
- amber and copper/orange junctions;
- small teal signal accents;
- decisive geometric framing softened by organic leaves, topographic contours,
  sunrise/radiant lines, and human-scale illustrations;
- substantial whitespace and readable editorial hierarchy;
- bold line art and simple modular illustrations rather than generic glossy
  AI-rendered objects.

Avoid:

- generic blue/purple SaaS gradients;
- neon cyberpunk dashboards;
- faux-terminal styling as the whole visual identity;
- dense monitoring screens on public informational pages;
- little houses on rolling green hills, holding-hands clichés, or generic
  sustainability stock imagery;
- parchment/victorian ornament that makes the project feel historical rather
  than forward-looking;
- excessive circuit decoration that competes with content.

The slight Frutiger Metro influence should appear through clear outlined
objects, optimistic diagrams, tactile icons, and network/route motifs—not
through glossy bubbles or early-2000s imitation.

## Product truth that overrides concept copy

The visual boards contain placeholder or outdated wording. Do not copy their
technical statements without checking current repository sources.

The project is an open-source platform for turning spare or retired Android
phones, computers, and SBCs into secure, remotely manageable self-hosting
nodes. Its Android application provisions and supervises Linux execution
environments—initially Termux-based environments and full QEMU virtual
machines—connects them to a private network, and exposes a narrowly scoped
management interface to an external controller. Established tools such as SSH,
Ansible, Docker Swarm, Kubernetes, Nomad, OpenTofu, and Nix continue to manage
workloads in their native formats.

The public site must not claim or imply:

- a product named **SalvageOS**;
- that the browser website controls nodes;
- that SalvageNet replaces workload orchestrators or configuration tools;
- broad device compatibility before published device evidence exists;
- production readiness, unattended reliability, or completed physical
  validation before the acceptance ledger supports those claims;
- invented user counts, adoption numbers, dates, performance metrics, or
  percentages;
- that every workload is encrypted end to end by SalvageNet itself;
- that arbitrary guest images are equally safe or supported;
- that an issue or pull request closing proves a product acceptance gate.

## Brand asset boundary

The logo presentation boards establish direction but are not suitable as the
only production source. Before launch, the website workstream should produce:

- a canonical vector wordmark and icon mark;
- transparent raster fallbacks;
- a monochrome mark;
- small favicon/app-icon variants tested at real sizes;
- explicit light and dark exports;
- a clear-space and minimum-size rule;
- source and licence records.

Do not redraw or simplify the logo ad hoc inside individual components. The
site should import one shared logo component with named variants.

## Design tokens to establish in WEB-01

The concept board suggests approximate values, but final tokens must be tested
for contrast and may be adjusted. Define semantic tokens rather than exposing
raw palette names throughout components.

Recommended token groups:

```text
colour.canvas
colour.surface
colour.surfaceRaised
colour.ink
colour.inkMuted
colour.border
colour.brandPrimary
colour.brandSecondary
colour.signal
colour.warning
colour.verified
colour.focus
colour.link
colour.danger
```

```text
space.1 … space.8
radius.small / medium / large
border.hairline / standard / strong
shadow.none / subtle / raised
motion.fast / standard / slow
layout.reading / content / wide
```

Use the same semantic token API in light and dark themes. Dark mode should feel
like the same calm material system at night, not a separate cyberpunk brand.

The design boards mention Space Grotesk for display and Inter for body/UI. The
first implementation may use metrically suitable system fallbacks until local,
licensed, performance-audited font files are committed. Do not make a remote
font service a runtime dependency.

## Page-system implications

The final homepage concept is a composition reference, not a literal page
specification. Preserve its strengths:

- clear opening proposition;
- one primary and one secondary action;
- compact trust/principle row;
- simple how-it-works sequence;
- modular benefits/use-case sections;
- strong central network/system illustration;
- decisive lower-page call to action;
- coherent footer and navigation.

Correct its weaknesses during implementation:

- do not overload the homepage with every roadmap or architecture detail;
- do not use fake account/profile controls before accounts exist;
- do not imply installation is a three-click consumer flow before it is tested;
- do not present unverified workloads, devices, or security guarantees as
  current features;
- use real copy from current project sources.

The roadmap should be a dedicated route, with only a compact current-status
summary on the homepage.

## Roadmap visual language

The circuit/route motif is well suited to milestones and dependencies. Use it
as a progressive visual layer over a semantic HTML structure.

A good roadmap composition has:

- a clearly highlighted current item;
- milestone sections that read as a journey;
- compact outcome cards;
- separate work-status and validation-status treatments;
- text dependency links such as **Waiting on GUEST-01**;
- a legend explaining implementation versus evidence;
- freshness and source information;
- optional dependency highlighting on wide screens.

Do not reduce the roadmap to a percentage, a single progress bar, or a canvas
node graph. The roadmap has multiple kinds of state and non-uniform outcomes.
See `website/docs/roadmap-integration.md` for the complete technical contract.

## Component character

Components should feel constructed rather than decorated:

- borders may include restrained circuit junctions or offset corners;
- buttons are solid, high-contrast, and clearly interactive;
- secondary actions remain visually quieter but not low-contrast;
- cards use a small set of compositional variants rather than unique art per
  page;
- icons use bold optimistic line work;
- diagrams use limited textures and purposeful labels;
- status chips always include text and a shape/icon;
- warnings remain unmistakable in both themes.

Circuit lines should not run through text, create false grouping, or become
interactive targets unless they have a real semantic purpose.

## Illustration guidance

Prefer simple editorial/system illustrations with a limited palette and real
technical relationships:

- phones, tablets, mini PCs, laptops, and servers as distinct device classes;
- a host device containing a managed Linux environment;
- a private-network relationship between host, guest, and controller;
- established external tools managing workloads;
- ownership, reversibility, recovery, and offline-capable operation;
- thermal, power, storage, and lifecycle constraints shown honestly when
  relevant.

Avoid generic server racks floating in clouds, anthropomorphic AI imagery,
perfectly symmetrical pseudo-diagrams, and unlabelled networks whose meaning
comes only from decorative lines.

## Accessibility and implementation

The visual system must survive:

- keyboard navigation;
- 200% zoom;
- narrow mobile layouts;
- high contrast requirements;
- System, Light, and Dark themes;
- reduced motion;
- no JavaScript;
- print and reader-mode use.

Decorative textures and route lines should be separate layers with
`pointer-events: none` and appropriate reduced-motion handling. Important
information stays in normal document flow.

A preview-only `/__design/` route should demonstrate tokens, typography,
buttons, cards, status combinations, roadmap nodes, warnings, empty/fallback
states, both themes, and reduced-motion behaviour before whole pages proliferate.

## Handoff deliverables for the design agent

Before the design foundation is considered ready for page implementation, it
should leave:

1. token definitions for light and dark themes;
2. shared logo and icon components using audited source assets;
3. page shell, header, footer, navigation, and theme control;
4. a component gallery;
5. roadmap card, milestone, status, dependency, validation, and freshness
   components;
6. responsive layout rules;
7. a compact illustration/pattern library;
8. content-state examples for normal, stale, fallback, blocked, deferred,
   under-review, implemented-but-unverified, and verified cases;
9. accessibility and visual-regression coverage;
10. documentation of any intentional divergence from the supplied boards.

The website workstream may refine visual decisions freely inside these
boundaries without changing MVP runtime code or the roadmap generator.
