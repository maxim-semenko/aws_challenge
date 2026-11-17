---
id: T03-08
title: "SPA: admin users table with paging, role line, admin-only nav"
phase: P3-rest-api-data
status: Review
agent: frontend
skills: [react-expert, spa-api-client, amplify-auth]
depends_on: []
blocked_by: []
design: ../../design/admin-api.md
spec: ../../specs/09-admin-page-and-role.md
acceptance: [AC-09.1, AC-09.2, AC-09.3, AC-09.4, AC-09.5]
---
# T03-08 — SPA: admin users table, role line, admin-only nav

## // BUSINESS CONTEXT

W3-G4, S6: the administrator sees all users in a read-only table; every user sees the own role on the personal page
(project requirements). The page is the visible end of the whole Week 3 chain.

## // TECHNICAL CONSTRAINTS

- Contract: spec 08 (`MeResponse` unchanged; new `User` and page types); UI states and texts: spec 09 exactly.
- Server data only through TanStack Query; access token per ADR-004 (existing `api/client.ts`); no request without
  `VITE_API_URL` (AC-04.10 must still hold).
- Profile values stay from `fetchUserAttributes` (Q-19 A); reuse `profile/format.ts` (`roleLine`, date, country).
- No styling tokens exist (CLAUDE.md §5): reuse the existing custom properties in `index.css`; no new literal colour
  values outside it.
- Unit tests with Vitest in Node (pure functions for state selection, paging line, cell formats); component tests
  with React Testing Library only if the owner approves the new dev dependencies (proposal from T02-05).
- Pre-task invariants: `npm run build` and `npm test` green.

## // SCOPE

**Implement**
- API client: `adminUsers(page)` endpoint and types; role line on the profile card; Admin link only for admins;
  `/admin` page with all states of spec 09; `RequireAuth` on `/admin` when the API is configured
- Unit tests for AC-09.1
- Update skill `spa-api-client` (endpoints, query keys, 403 handling)

**Exclude**
- Sorting UI, filters, editing, Chat (Week 5)

**Interfaces that must match**
- Query keys `['me']`, `['admin','users',page]`; field names of spec 08.

## Definition of Done

- [x] Build and tests green (AC-09.1, AC-09.2)
- [ ] AC-09.3 … AC-09.5 verified on the deployed SPA after T03-07, evidence in Notes
- [x] Skill updated
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-19. No `depends_on`: the code is written against spec 08;
  AC-09.3 … AC-09.5 can only be verified once T03-07 is deployed.
- 2026-11-13: Q-19 A accepted by the owner; design admin-api `Accepted` → `Todo`, start gate holds; scope unchanged.
- 2026-11-16 (frontend): start gate held; pre-task `npm test` (48) and `npm run build` green → `In progress`.
  Implemented against the spec 08 contract (T03-06/T03-07 not deployed):
  - `src/config/amplify.ts` `isApiConfigured` (= `VITE_API_URL` set and auth configured);
    `src/api/client.ts` types `User`, `Page<T>`, `adminUsers(page)` (`?page=<p>&size=20`, default sort),
    `adminUsersQueryKey`, retry rule `retryApi` (4xx never, 5xx/network once); `src/api/queries.ts` `useMe`,
    `useAdminUsers` (`keepPreviousData`), `useSignOutOnUnauthorized` (401 → sign-out, `/sign-in`).
  - Role line on the profile card (`profile/Profile.tsx`, `selectRoleLine` in `profile/format.ts`), mounted only
    with `isApiConfigured`; Admin nav link only when `/api/me` groups contain `admin` (`App.tsx`); `/admin` wrapped in
    `RequireAuth` when the API is configured; `pages/AdminPage.tsx` with all spec 09 states, pure logic in
    `admin/view.ts`; table styles in `App.css` from the existing custom properties only (no new literal colours).
  - Skills updated: `spa-api-client` (endpoints, query keys, 401/403/retry handling), `amplify-auth` (header, guard).
- 2026-11-16 AC-09.1 **pass (local)**: `npm test` 7 files / 69 tests green (new: `api/client.test.ts` — path,
  query keys, retry rule; `admin/view.test.ts` — state selection 403/401/error/empty/data/unconfigured, error over
  stale data, paging line first/middle/last/`total = 0`/beyond the end, columns, cell formats date/country/null/odd
  values; `profile/format.test.ts` — role line from the query state); `npm run build` (`tsc -b` + vite) green.
  Component tests not written (React Testing Library needs owner approval of new dev dependencies).
- 2026-11-16 AC-09.2 **pass (local)**: no `.env*` besides `.env.example` (all `VITE_*` empty); `npm run preview`
  rendered headless in Chrome with a net log: `/` shows the intro without auth/Chat/Admin links, `/admin` shows
  "Users" + "Not available yet — coming in a later week."; the only app requests were `/`, `/admin`, the JS/CSS
  assets and `favicon.svg` — no `/api` request.
- AC-09.3, AC-09.4, AC-09.5: **not verified** — need T03-07 deployed (routes, CORS) and owner screenshots from the
  deployed SPA with `VITE_API_URL` set in Amplify Hosting. The configured path (real `/api/me` and
  `/api/admin/users` responses, 401 sign-out, 403 text) is covered only by the pure-function unit tests, not run
  against an API. AC-09.5 with fewer than 21 users on `dev` falls back to the paging unit tests above.
- PLAN.md not edited by this agent (parallel work); its T03-08 row must read `Review`.
- ARCH review 2026-11-16 (light, contract only): **pass**. `src/api/client.ts` types `MeResponse`, `User`,
  `Page<T>` match spec 08 §Outputs field for field (incl. `updatedAt`, nullability); paths `/api/me` and
  `/api/admin/users?page=<p>&size=20` (default sort, size within 1..100) and query keys `['me']`,
  `['admin','users',p]` match spec 08/09; 401 → sign-out, 403 → no-access, 4xx not retried per the spa-api-client
  skill; no token logging. Re-run by ARCH: `npm test` 69 passed, `npm run build` green. AC-09.3 … AC-09.5 remain
  **not verified** until T03-07 is deployed (CORS origins incl. `http://localhost:5173` and routes come from T03-07;
  ENVIRONMENT.md still shows the Week 2 routes/CORS). No findings.
- 2026-11-17 **owner decision:** the HTTP API follows the curriculum diagram strictly — only `GET /admin` (users list
  for admins) and `POST /chat` (Week 5); no `/api/me`, no `/api/admin/users`. Frontend changed accordingly (status
  stays `Review`):
  - Role line and Admin nav link from the access token claim `cognito:groups` via `fetchAuthSession()` — no API call
    (`auth/session.ts` `useGroups`, key `['groups', userId]`, dropped by sign-out; pure `groupsFromClaims` in
    `profile/format.ts`). "Role: administrator" if it contains `admin`, else "Role: user"; "Role: unavailable" only
    if the session cannot be read. The role line is now shown whenever the profile is shown (no `VITE_API_URL`
    needed).
  - Admin page calls `GET /admin?page=<p>&size=20` (`adminUsersPath`); response shape, 401/403/retry rules and the
    "no request without `VITE_API_URL`" behaviour unchanged. Removed `endpoints.me`, `MeResponse`, `meQueryKey`
    (`['me']`), `useMe`.
  - Skills `spa-api-client` and `amplify-auth` updated. The "Interfaces that must match" line above (`['me']`) and
    the `/api` prefix rule of CLAUDE.md §6 are superseded by this decision (docs owned by other agents).
  - `npm test` 7 files / 70 tests green; `npm run build` green. `npm run preview` not re-run (AC-09.2 path unchanged:
    `AdminPage` still renders `ComingLater` without `VITE_API_URL`) — **not verified** after this change.
