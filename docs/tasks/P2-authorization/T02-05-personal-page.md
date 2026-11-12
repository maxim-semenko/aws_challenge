---
id: T02-05
title: "Personal page from Cognito attributes; API client with the access token; role from GET /api/me"
phase: P2-authorization
status: In progress
agent: frontend
skills: [react-expert]
depends_on: [T02-03, T02-04]
blocked_by: []
design: ../../design/authentication.md
spec: [../../specs/04-user-registration-and-sign-in.md, ../../specs/05-protected-api.md]
acceptance: [AC-04.6, AC-04.7]
---
# T02-05 — Personal page from Cognito attributes; API client with the access token; role from GET /api/me

## // BUSINESS CONTEXT

W2-G2: after sign-in the user sees the own registration data and nothing to edit. The role line, read from the
protected API, is the visible proof that the SPA reaches a Lambda in the VPC only with a valid token (W2-G3).

## // TECHNICAL CONSTRAINTS

- ADR-013: profile values from `fetchUserAttributes` (Cognito), no database this week.
- ADR-004: the API client sends `Authorization: Bearer <access token>` (fixes the ID token in the draft
  `frontend/src/api/client.ts`); base URL from `VITE_API_URL`.
- `fetchUserAttributes` and `GET /api/me` through TanStack Query; the `me` response type exactly as spec 05 §Outputs.
- Display rules and states exactly as spec 04 §Outputs and §Edge Cases; date shown `DD/MM/YYYY`; country as name +
  code; role line from `groups`.
- Read-only: no input, edit or save controls.
- Only the `me` endpoint and its types change in the API client; remove the Vite `/api` proxy to `:8080` (the local
  backend no longer exists, ADR-015); other draft endpoints stay untouched.
- Pre-task invariants: `npm run build` green.

## // SCOPE

**Implement**
- Personal page at `/me`, API client token change, `me` response type per spec 05, Vite proxy removal
- Tests for the page states (attributes loaded, attribute missing, attribute error, API error → "Role: unavailable")
  with mocked Amplify/API responses
- Skill file `spa-api-client` (base URL, token, error handling by status, TanStack Query keys; skills ownership rule)

**Exclude**
- Admin and chat pages, styling, profile editing

**Interfaces that must match**
- Field names and types exactly as spec 05 §Outputs; attribute names as spec 04 §Inputs.

## Definition of Done

- [ ] Build green; tests green
- [ ] AC-04.6, AC-04.7 verified against dev, evidence in Notes (no token values)
- [x] Skill file added
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-12 — **Start gate not met, started on the owner's explicit request:** T02-03 (HTTP API) is not done and
  T02-04 is in `Review`. Only the part that does not need the API is finished; the task stays `In progress`.
- Implemented: `src/pages/MePage.tsx` (read-only `<dl>` from `fetchUserAttributes` via TanStack Query key
  `['user-attributes']`; loading, error + "Retry" without stale data), `src/profile/format.ts` (date `DD/MM/YYYY`,
  country "Name (CODE)", "—" for missing/unparseable, out-of-range values as stored, role line). API client:
  `Authorization: Bearer <access token>` (was the ID token), `MeResponse` per spec 05 §Outputs, `meQueryKey`; the
  role query runs only when `VITE_API_URL` is set, otherwise "Role: unavailable"; 401 → sign-out and `/sign-in`, not
  retried. Vite `/api` proxy removed. Skill [spa-api-client](../../../.claude/skills/spa-api-client/SKILL.md) added.
- Tests: `src/profile/format.test.ts` covers the display rules (date, country, missing, out-of-range, role lines) —
  green. **Open:** page-state tests with mocked Amplify/API responses need React Testing Library + jsdom (new dev
  dependencies, not added yet).
- **Not verified:** AC-04.6, AC-04.7 (need the dev pool, T02-03 and `VITE_API_URL`).
