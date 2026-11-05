---
id: T00-04
title: "SPA builds and renders without Cognito/API configuration"
phase: P0-foundation
status: Todo
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
- Pre-task invariants from CLAUDE.md: `npm run lint` and `npm run build` green; CSS bundle size check.

## // SCOPE

**Implement**
- `npm ci && npm run lint && npm run build` green
- Home page renders with all `VITE_*` empty (auth UI hidden, no runtime error in the console)

**Exclude**
- Removing template leftovers, auth UI, API client, styling

**Interfaces that must match**
- Build output stays in `frontend/dist` (used by `amplify.yml`).

## Definition of Done

- [ ] Lint and build green; `npm run preview` with an empty `.env` shows the home page and `/chat` reload works
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes
