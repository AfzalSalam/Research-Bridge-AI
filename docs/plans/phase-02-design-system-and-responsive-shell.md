# Phase 02 — Design System and Responsive Shell

**Status:** Complete

**Prepared:** 2026-07-31

**Scope:** Project-owned visual tokens, typography, accessible UI primitives,
responsive navigation, honest route shells, reusable data-state patterns, and a
component gallery only

## 1. Outcome

Turn the approved Figma Make direction into a maintainable frontend foundation
that future product screens can reuse without regenerating the application.

At the end of this phase:

- the teal/indigo editorial-academic direction is represented by semantic
  project tokens rather than arbitrary values;
- Source Serif 4 and Manrope are bundled through local Fontsource packages, so
  production builds do not depend on the Google Fonts network;
- reusable shadcn/ui-based primitives provide accessible buttons, badges,
  fields, separators, skeletons, and a mobile navigation sheet;
- every planned placement-release destination has an honest, non-functional
  route shell;
- the header and navigation work with keyboard, touch, narrow viewports, and
  200% zoom;
- loading, empty, error, partial, and unavailable states have reusable visual
  patterns;
- a component gallery documents the visual language in running code;
- the existing typed health boundary remains functional and is restyled using
  the new system.

This phase creates the visual grammar. It does not implement profile forms,
search, mentor results, outreach, opportunities, tracking, or mock data.

## 2. Starting state

- Phase 1 is committed as `fd3a243`, and the working tree is clean.
- The frontend has strict TypeScript, Tailwind CSS 4, Vitest, and a single
  dynamic foundation page.
- The current CSS already previews a warm neutral, teal, and indigo direction,
  but it does not expose a complete semantic token system or reusable UI
  primitives.
- The header is page-specific and has no product navigation.
- No shadcn/ui configuration, Lucide icon dependency, mobile menu, route shell,
  state pattern, or component gallery exists.
- The FastAPI application and database configuration are outside this phase and
  must remain unchanged.

## 3. Figma Make audit

The Figma connector was used first and returned the Make source manifest. The
running prototype was then inspected at desktop and mobile sizes through its
live preview because the source-resource contents and node screenshot were not
exposed by this client.

### Reuse as design intent

- warm neutral canvas `#fcfaf8` and white reading surfaces;
- near-black ink, quiet gray supporting text, and hairline borders;
- restrained teal `#1a746b` and indigo `#3b426e` accents;
- Manrope for interface text and Source Serif 4 for display/editorial text;
- large, calm headings with generous whitespace;
- flat, scannable lists rather than repeated floating cards;
- an editorial desktop mentor master-detail relationship;
- evidence-led labels and a clear primary action hierarchy;
- the open-book brand motif, represented with the matching Lucide glyph rather
  than a newly drawn icon.

### Correct before reuse

- Mobile navigation disappears entirely; it needs a visible, labelled menu.
- At 390 pixels, the landing and mentor views collapse into extremely narrow
  columns with large blank regions. Mobile must use a task sequence rather than
  squeezing the desktop master-detail grid.
- Mentor rows use clickable `<div>` elements without button/link semantics,
  keyboard access, or visible focus.
- The prototype contains unsupported claims such as `Verified active`,
  `Accepting students`, `Top 5%`, and `~40%` estimated response rate.
- The `Top 100` institution filter is undefined and conflicts with the product
  non-goals.
- `Student Portal` duplicates the Profile destination.
- Generated Vite structure, dependencies, and mock content do not belong in the
  Next.js architecture.

### Product-safe replacements

- Use `Unknown`, `Unconfirmed`, `Source needed`, or `Last verified …` when
  evidence is absent or stale.
- Demonstrate relevance as a labelled UI pattern only; do not add values,
  ranking, paper counts, or mentor records in this phase.
- Route shells state clearly that functionality arrives in Phase 3.
- Use one Profile destination and reserve the main navigation for Discover,
  Mentors, Opportunities, and Applications.

## 4. Design system architecture

```text
RootLayout
  -> self-hosted variable fonts
  -> SkipLink
  -> SiteHeader
      -> desktop navigation
      -> mobile Sheet navigation (only client boundary)
  -> route content

globals.css
  -> semantic source tokens
  -> Tailwind @theme inline mappings
  -> base typography/focus/selection rules
  -> reduced-motion and forced-colors considerations

components/
  ui/                 shadcn-derived primitives owned by the repository
  brand/              logo and wordmark
  navigation/         responsive application navigation
  layout/             container, page header, section structures
  states/             loading/empty/error/partial/unavailable patterns
```

Most components remain Server Components. Only the pathname-aware navigation
and mobile Sheet require `"use client"`.

## 5. Token decisions

### Color roles

| Token role | Initial value | Intended use |
| --- | --- | --- |
| canvas | `#fcfaf8` | Main warm background. |
| surface | `#ffffff` | Reading and control surfaces. |
| ink | `#1a1a19` | Primary text. |
| ink-strong | `#151618` | Primary buttons and strongest headings. |
| muted | `#666562` | Supporting text that still passes contrast. |
| line | `#e8e6e1` | Hairline dividers and control boundaries. |
| teal | `#1a746b` | Evidence, success, and active selection. |
| teal-soft | `#e5f0ef` | Quiet evidence background. |
| indigo | `#3b426e` | Brand mark and editorial emphasis. |
| indigo-soft | `#eef0f8` | Quiet brand background. |
| amber | accessible dark amber | Unknown, stale, or needs-verification state. |
| danger | accessible muted red | Errors and destructive semantics only. |

Token names are semantic in components. Raw Figma hex values appear only in the
token definitions.

### Typography

- Source Serif 4 variable font: display headings, evidence titles, and editorial
  moments.
- Manrope variable font: navigation, forms, metadata, and body copy.
- Load each font once in the root layout through local Fontsource variable-font
  packages, expose CSS variables, and provide robust serif/sans fallbacks.
- Maintain readable measure, fluid heading sizes, minimum 16-pixel form text,
  and line heights suitable for 200% zoom.

### Shape, spacing, and effects

- Use a four-pixel base spacing rhythm with named container and section gaps.
- Keep radii small: two to eight pixels depending on control role.
- Prefer borders and whitespace over shadows.
- Use one restrained elevation token only for the mobile Sheet.
- Use short opacity/color transitions; remove them under reduced motion.

## 6. Dependencies and why they exist

| Dependency | Reason |
| --- | --- |
| `@fontsource-variable/manrope` and `@fontsource-variable/source-serif-4` | Bundle the approved typography locally and keep production builds independent of Google Fonts availability. |
| `lucide-react` | Approved icon system; includes a matching open-book mark and consistent accessible icon geometry. |
| `class-variance-authority` | Typed visual variants for repository-owned shadcn buttons and badges. |
| `clsx` | Conditional class composition without string branching. |
| `tailwind-merge` | Resolves conflicting Tailwind utilities when consumers extend primitives. |
| `radix-ui` selected by the current shadcn CLI | Accessible focus management, dismissal, labelling, and portal behavior for the mobile Sheet. |
| `tw-animate-css` | Small state-driven Sheet entry/exit utilities; reduced-motion rules remain authoritative. |

The shadcn CLI copies component source into the repository; it is not treated as
a remote black-box component library. Generated files must be inspected and
adapted to the project tokens.

Do not add TanStack Query, React Hook Form, Zod, Motion, Playwright, or product
data dependencies in this phase because no server state, real form, product
animation, or end-to-end fixture journey is being implemented yet.

## 7. Route shells

| Route | Purpose in Phase 2 |
| --- | --- |
| `/` | Editorial landing/foundation status using the real health boundary. |
| `/profile` | Honest profile-shell placeholder. |
| `/discover` | Honest research-discovery-shell placeholder. |
| `/mentors` | Honest mentor-workspace-shell placeholder. |
| `/opportunities` | Honest verified-opportunities-shell placeholder. |
| `/applications` | Honest application-tracker-shell placeholder. |
| `/design-system` | Internal component gallery and state documentation. |

Route shells share layout and navigation but contain no fake results, forms, or
business actions. They provide stable destinations for Phase 3.

## 8. Component milestones

### A. Foundations

- [x] Initialize shadcn for the existing Tailwind 4/React 19 `src` project.
- [x] Add semantic design tokens and Tailwind mappings.
- [x] Add self-hosted Manrope and Source Serif 4 typography.
- [x] Add global focus, selection, reduced-motion, and layout rules.
- [x] Add the shared `cn` utility.

### B. Accessible primitives

- [x] Add and adapt Button, Badge, Input, Separator, Skeleton, and Sheet.
- [x] Add Field primitives with explicit labels, descriptions, and errors.
- [x] Add evidence/verification status variants without unsupported claims.
- [x] Ensure icons are decorative by default or have an accessible name.

### C. Responsive shell

- [x] Move the brand/header into the root layout.
- [x] Add a visible skip link and consistent `main` target.
- [x] Add pathname-aware desktop navigation with `aria-current`.
- [x] Add an accessible mobile Sheet menu with a 44-pixel trigger.
- [x] Ensure navigation remains available at narrow widths and zoom-equivalent
  narrow layouts.
- [x] Add shared Container, PageHeader, GallerySection, and RouteShell
  components.

### D. States and documentation

- [x] Add loading, empty, error, partial, and unavailable patterns.
- [x] Restyle the health boundary using the new primitives.
- [x] Add honest route-shell pages.
- [x] Add the `/design-system` component gallery.
- [x] Document intended usage and anti-patterns in the gallery and learning log.

### E. Validation

- [x] Add focused primitive, navigation, and state tests.
- [x] Run lint, strict type-check, Vitest, and production build.
- [x] Inspect all routes at desktop and mobile widths.
- [x] Verify no horizontal overflow at 360, 390, 768, and 1280 pixels.
- [x] Verify keyboard navigation, focus visibility, menu dismissal, and route
  labels.
- [x] Verify reduced-motion behavior and semantic landmarks.
- [x] Run the production npm audit and record development-only advisories.
- [x] Update `docs/LEARNING_LOG.md`.
- [x] Review the complete diff and secret scan.

## 9. Validation commands

```powershell
npm.cmd install
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd audit --omit=dev --audit-level=high
```

Browser verification used the local Next.js development server. The health
card was checked first with FastAPI stopped and then with the real versioned
health endpoint available.

The backend source is unchanged, but its existing checks may be rerun as a
regression safeguard before completion.

## 10. Accessibility acceptance criteria

- One banner, navigation, and main landmark per route.
- A visible skip link appears on keyboard focus.
- Navigation uses links, not click-only containers.
- The current destination uses `aria-current="page"`.
- The mobile menu has an accessible name, focus containment, Escape dismissal,
  and focus return.
- Every interactive target is at least 44 by 44 CSS pixels where practical.
- Text and meaningful UI colors meet WCAG AA contrast.
- Layout remains usable at 200% zoom and does not depend on horizontal scroll.
- Loading indicators expose a useful text alternative.
- State is never communicated by color alone.
- Reduced-motion users receive no non-essential movement.

## 11. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Figma code is pasted into Next.js | Use computed intent and screenshot evidence only; implement against project conventions. |
| The gallery becomes a second application | Keep it documentation-only and build product behavior in Phase 3. |
| Route placeholders look like finished features | Label each shell clearly with its implementation phase and omit fake controls/data. |
| shadcn initialization overwrites approved CSS | Start from the committed Phase 1 baseline, inspect every generated file, and reapply project tokens deliberately. |
| Mobile Sheet makes the whole layout client-rendered | Isolate the client boundary to navigation; keep route content server-rendered. |
| Font loading makes builds network-fragile | Bundle the approved variable fonts through local Fontsource packages and verify the production build without a Google Fonts request. |
| Decorative polish reduces accessibility | Use contrast checks, visible focus, semantic tests, reduced motion, and browser verification as completion gates. |
| Unsupported Figma claims leak into UI | Use neutral status samples and explicit unknown/unconfirmed language only. |

## 12. Rollback strategy

- Phase 1 remains recoverable as commit `fd3a243`.
- Keep Phase 2 in one reviewable commit after validation and acceptance.
- Generated shadcn files are repository-owned and can be reverted with the
  Phase 2 commit; never reset the repository destructively.
- No backend, database, or external state is mutated in this phase.

## 13. Out of scope

- Typed product fixtures and real product forms.
- Mentor cards, ranking values, paper records, evidence records, or outreach
  drafts.
- TanStack Query, React Hook Form, Zod, or product state management.
- API contract expansion or backend changes.
- Database schema or persistence.
- OpenAlex or other academic providers.
- LLMs, email generation, LangGraph, or automated email sending.
- Authentication and private data.
- Dark mode, localization, and a public Storybook deployment.

## 14. Completion rule

Phase 2 is complete only when the design system is project-owned, the route
shell is responsive and keyboard accessible, the mobile failures observed in
Figma are absent, the component gallery documents every core state, all quality
gates pass, the learning log is updated, and the diff contains no product logic
from later phases.

The exact next step after acceptance is **Phase 3 — Typed mock product
journey**, beginning with a new execution plan and typed fixture contracts.

## 15. Results

- Figma Make was treated as visual evidence, not an application source tree.
  The editorial hierarchy, warm canvas, book motif, teal, and indigo were
  retained; disappearing mobile navigation, squeezed columns, click-only rows,
  duplicate destinations, and unsupported claims were rejected.
- The first production build exposed Google Fonts as a network dependency.
  Local Fontsource variable packages replaced `next/font/google`, and the
  subsequent production build completed without external font retrieval.
- The responsive route matrix checked every route at 360, 390, 768, and 1280
  CSS pixels: all 28 combinations had one `main`, one `h1`, and zero horizontal
  overflow. A long typography specimen discovered during that pass was reduced
  at the smallest breakpoint and rechecked.
- Contrast checks for the shipped text pairs range from 5.37:1 for teal on the
  warm canvas to 16.73:1 for body ink on canvas; evidence buttons, muted copy,
  indigo, unknown, and error treatments all meet the WCAG AA text threshold.
- The component suite contains 11 passing tests across five files. Navigation
  tests cover current-route semantics, the labelled mobile dialog, Escape
  dismissal, and focus return. State tests cover loading, error, partial, and
  status semantics.
- Frontend lint, strict TypeScript, tests, and production build pass. Backend
  Ruff, formatting, mypy, and two existing Pytest tests pass, and Compose
  configuration remains valid.
- The production npm dependency graph reports zero vulnerabilities. The full
  audit still reports the already documented development-only Brace Expansion
  advisory in the ESLint/Next lint graph; its available automatic fix requires
  a breaking ESLint 10 upgrade.
- No backend source, schema, product fixture, ranking calculation, LLM workflow,
  or persistence behavior was added.
