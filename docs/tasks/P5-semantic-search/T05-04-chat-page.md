---
id: T05-04
title: "SPA: admin-only /chat page — form, debounced request, generic results table, states"
phase: P5-semantic-search
status: Review
agent: frontend
skills: [react-expert, spa-api-client, amplify-auth]
depends_on: []
blocked_by: []
design: ../../design/semantic-search.md
spec: ../../specs/13-chat-page.md
acceptance: [AC-13.1, AC-13.2]
---
# T05-04 — Admin AI search page `/chat`

## // BUSINESS CONTEXT

Week 5 S1 and the project requirement: the administrator opens a separate page, types a question in "human" language
and sees rows or statistics from the user base. Automatic requests must not burn LLM tokens on half-typed questions.

## // TECHNICAL CONSTRAINTS

- Conventions: strict TypeScript, server data through TanStack Query, configuration only via `VITE_*`, the
  `spa-api-client` rules (Bearer access token, 401 sign-out); no new npm dependency; no design tokens yet (plain CSS
  classes already in `index.css` / `App.css`, CLAUDE.md §5).
- Request and response fields exactly as spec 12 §Inputs/§Outputs (body `{"query"}` only); UI states, debounce rule
  (800 ms, ≥ 3 characters, vector mode only; `sql` only on Search / Enter), no retry, cache per text, messages and
  table formatting exactly as spec 13.
- Admin-only: Chat link and page from `cognito:groups` (existing `useGroups`); empty `VITE_API_URL` → existing
  placeholder, no request (AC-04.10 still holds).
- Tests only what AC-13.1 lists (pure functions in a small view module, Vitest); no E2E.

## // SCOPE

**Implement**
- `frontend/src/api/client.ts` (`ChatRequest`/`ChatResponse` types, `endpoints.chat`), a chat hook in
  `api/queries.ts`, `frontend/src/chat/view.ts` (+ test), `pages/ChatPage.tsx`, header link in `App.tsx`, route guard
  as `/admin`
- Skill `spa-api-client`: `POST /chat` (no retry, key, cache rule)

**Exclude**
- API or Lambda changes; styling system; deploy (owner push → Amplify; checked in T05-03)

**Interfaces that must match**
- spec 12 response shape (`mode`, `columns`, `rows`, `rowCount`, `truncated`, `sql`, `timings`, `tokens`,
  `modelId`); error statuses 400/401/403/429/500/502.

## Definition of Done

- [ ] `npm run build` and `npm test` green (AC-13.1); AC-13.2 self-check in Notes
- [ ] Skill updated
- [ ] Status updated here (`Review`) and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-25: created by Week 5 planning; `Todo` — no open blocker (the page does not depend on Q-21 … Q-23); starts
  when the design semantic-search is `Accepted`.
- 2026-11-25: design semantic-search `Accepted` (owner) — startable.
- 2026-11-25 (frontend): implemented — `api/client.ts` (`ChatRequest`, `ChatResponse`, `chatQueryKey`,
  `endpoints.chat`), `api/queries.ts` `useChat`, `chat/view.ts` + `chat/view.test.ts`, `pages/ChatPage.tsx`,
  `App.tsx` (Chat link admin-only, `/chat` in `RequireAuth` when the API is configured); skills `spa-api-client`
  and `amplify-auth` updated. No new dependency, no new CSS.
  - AC-13.1: `npm test` 8 files / 78 tests passed (new `chat/view.test.ts`: 8 tests — mode rule, automatic-request
    rule, status → message, cell formatting); `npm run build` (`tsc -b && vite build`) green.
  - AC-13.2 self-check: body built only in `client.ts` `chat()` as `{ query }` with the trimmed text; `useChat` has
    `retry: false`, `refetchOnWindowFocus: false`, `refetchOnReconnect: false`, `staleTime` 60 s; no
    `dangerouslySetInnerHTML` in `frontend/src` (grep); Chat link rendered only with `admin` in the token groups,
    `/chat` shows the no-access text to non-admins before `useChat` is mounted; with empty `VITE_API_URL`
    `ChatPage` returns the `ComingLater` placeholder before any hook and `useChat` is disabled (`isApiConfigured`).
  - Not verified locally in a browser (`npm run preview` needs a configured pool/API for the page states);
    AC-13.3 … AC-13.5 are owner checks on the deployed SPA (T05-03 / T05-05).
