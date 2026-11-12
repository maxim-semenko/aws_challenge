---
id: T00-04
title: "SPA builds and renders without Cognito/API configuration"
phase: P0-foundation
status: Done
agent: frontend
skills: [react-expert]
depends_on: []
blocked_by: []
design: ../../design/spa-hosting.md
spec: ../../specs/01-spa-delivery.md
acceptance: [AC-01.2]
---
# T00-04 — SPA builds and renders without Cognito/API configuration

## // BUSINESS CONTEXT

Week 1 publishes the SPA before Cognito and the API exist. The draft in `frontend/src` was written before the plan
(R-04) and configures Amplify Auth at start-up; if it crashes on empty `VITE_*` values, the deployed site is a blank
page and W1-G1 fails.

## // TECHNICAL CONSTRAINTS

- React 19 + Vite + strict TypeScript; configuration only from `VITE_*`.
- Change only what blocks the build or the render without configuration — no new features, no redesign.
- Pre-task invariants from CLAUDE.md: `npm run build` green.

## // SCOPE

**Implement**
- `npm ci && npm run build` green
- Home page renders with all `VITE_*` empty (auth UI hidden, no runtime error in the console)

**Exclude**
- Removing template leftovers, auth UI, API client, styling

**Interfaces that must match**
- Build output stays in `frontend/dist` (used by `amplify.yml`).

## Definition of Done

- [ ] Build green; `npm run preview` with an empty `.env` shows the home page and `/chat` reload works
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-05 (started on the owner's direct request, before spa-hosting is Accepted): IDE import errors were caused
  by dependencies not installed (`node_modules` held only the Vite template). `npm ci` from the lockfile fixed them;
  `tsc -b` and `vite build` green. Open: (1) `npm run lint` fails — oxlint 1.89 needs Node ≥ 22.12, local Node is
  22.11.0, so npm skipped the optional `@oxlint/binding-win32-x64-msvc`; (2) CSS budget violated: 317 410 bytes,
  mostly `@aws-amplify/ui-react` styles (limit 10 240); (3) JS bundle 811 kB (Vite chunk-size warning).
- 2026-11-12 (owner): oxlint and the CSS budget removed from the project, so open items (1) and (2) no longer
  apply. `npm run build` green on Node 22.11.0 after removing oxlint.
- 2026-11-12: `Done` — accepted by the owner (evidence: owner's statement + console screenshot); the SPA is built and served by the manually built Amplify Hosting; agents have no AWS access.
