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
- 2026-11-13 — **Owner decision after testing the deployed SPA: profile on Home.** `pages/MePage.tsx` moved to
  `profile/Profile.tsx` (heading "My profile"); `pages/HomePage.tsx` shows it for a signed-in user, otherwise a short
  intro with sign-in / sign-up links. Route `/me` and the "My page" link removed (`/me` → `/` by the catch-all route).
  **"Failed to fetch" fix:** the draft "API: unreachable" health line and "Who am I (claims from the JWT)" block on
  Home removed; the role line is mounted only when `VITE_API_URL` is set (no line at all otherwise; 5xx/network still
  "Role: unavailable"); `/admin` and `/chat` render "Not available yet" and make no request without `VITE_API_URL`
  (no new Admin/Chat features). Spec 04, design authentication and skills `amplify-auth`, `spa-api-client` updated.
  The title and scope of this task still say "Personal page at `/me`"; spec 04 is the reference.
- Evidence (2026-11-13, local): build and tests green (see T02-04 Notes); with all `VITE_*` empty, headless Chrome
  shows zero console messages and zero API requests on `/`, `/chat`, `/admin`. Page-state tests with mocked
  Amplify/API responses are still **open** (no React Testing Library / jsdom yet). AC-04.6, AC-04.7 **not verified**.
- 2026-11-13 — **Owner request: layout; Admin/Chat placeholders.** Profile as a centered card "My profile": `<dl>`
  rows as a two-column grid (muted label, value), separators between rows; the role line, when rendered, is a small
  badge in the card ("Role: unavailable" on 404/5xx/network kept, spec 04). **Admin "Failed to fetch" fix:** with
  `VITE_API_URL` set, the draft Admin page called `GET /api/admin/users`, which does not exist in Week 2 (spec 05 has
  only `GET /api/me`, `GET /api/admin/ping`; the users list is Week 3). `/admin` ("Users") and `/chat` ("Chat") now
  render `pages/ComingLater.tsx` — "Not available yet — coming in a later week." — and make no request whatever
  `VITE_API_URL` is. Draft client functions `health`, `search`, `users` and types `DocumentSearchResult`, `UserDto`,
  `PageResponse` removed from `api/client.ts` (no other user); `endpoints` keeps only `me`. Skill `spa-api-client`
  and design authentication (routes table) updated. Spec 04 unchanged: the placeholder text still contains "Not
  available yet" (AC-04.10).
- Evidence (2026-11-13, local): tests and build green; with `VITE_API_URL=https://dummy-api.invalid` and the public
  pool ids, `/admin` and `/chat` at 1280px and 360px show the placeholder with zero external requests and zero console
  messages (details in T02-04 Notes). Profile card layout **not verified** (needs a signed-in session).
