---
name: spa-api-client
description: How the SPA in frontend/ calls the protected HTTP API — base URL from VITE_API_URL, the Cognito access token in the Authorization header, error handling by status (401 sign-out, 403 no-access, retry rule) and the TanStack Query keys. Use when adding or changing an API call in frontend/src/api or a page that reads API data.
license: MIT
metadata:
  domain: frontend
  triggers: API client, fetch, VITE_API_URL, Authorization, Bearer, access token, GET /admin, POST /chat, TanStack Query, queryKey, 403, paging
  role: specialist
  scope: implementation
  related-skills: react-expert, amplify-auth
  source: project (created by T02-05; endpoints, query keys and 403 handling updated by T03-08; /api/me removed, path GET /admin per owner decision 2026-11-17; POST /chat added by T05-04)
  used-by: [frontend]
---

# SPA API client

Conventions: CLAUDE.md §6. Endpoint fields: [spec 08](../../../docs/specs/08-admin-api.md) §Outputs (single home);
UI states and texts: [spec 09](../../../docs/specs/09-admin-page-and-role.md).

**Owner decision 2026-11-17:** the HTTP API follows the curriculum diagram — only `GET /admin` (users list for
admins) and, in Week 5, `POST /chat`. There is no `/api/me` and no `/api/admin/users`; the user's role comes from
the access token (`amplify-auth` skill, `useGroups`), not from the API.

## Client (`frontend/src/api/client.ts`)

- Base URL: `env.apiUrl` from `VITE_API_URL` (trailing `/` removed, no default). No local backend (ADR-015).
- `isApiConfigured` (`config/amplify.ts`) = `VITE_API_URL` set **and** auth configured (every route needs a token).
  Without it the SPA makes **no** API request: `AdminPage` shows the `ComingLater` placeholder and does not mount
  the users query; `useAdminUsers` is disabled as well (AC-04.10). `ChatPage` does the same (placeholder, `useChat`
  not mounted and disabled).
- Token: `fetchAuthSession()` → `tokens.accessToken` → `Authorization: Bearer <access token>` (ADR-004; the handler
  rejects the ID token). Amplify refreshes expired tokens inside `fetchAuthSession()`. Never log the header or token.
- Errors: non-2xx → `ApiError(status)` (the problem+json body is not parsed; the UI texts come from spec 09).
  Network failure → the `fetch` `TypeError`.
- Retry rule `retryApi`: 4xx never retried (401, 403, 400, 404, 429); 5xx and network errors retried once. Every
  API query sets `retry: retryApi` — except `POST /chat`: `retry: false` (each call may cost LLM tokens).

## Status handling

| Status | Behaviour |
|---|---|
| 401 | `useSignOutOnUnauthorized(error)` (`api/queries.ts`) → `useSignOut()` (cache cleared, `/sign-in`). Called once per query: `AdminPage` for the users list, `ChatPage` for the chat query |
| 403 | page-specific no-access state (`/admin`, `/chat`: "You do not have access to this page."), no table |
| 5xx / network | `/admin` "Users could not be loaded." + Retry; an error always wins over placeholder data |
| `/chat` 400 / 429 / 502 / other | texts of spec 13 §Outputs via `chat/view.ts` `chatErrorMessage`; no Retry button (Search sends again) |

## Endpoints, types and query keys

| Endpoint | Type | Query key | Hook / used by |
|---|---|---|---|
| `GET /admin?page=<p>&size=20` (default sort, no `sort` param) | `Page<User>` `{ items, page, size, total }` | `adminUsersQueryKey(p)` = `['admin','users',p]` | `useAdminUsers(page)` — `placeholderData: keepPreviousData` (previous page visible while the next loads; paging buttons disabled meanwhile); `/admin` |
| `POST /chat` body exactly `{"query": <trimmed>}` (`ChatRequest`; fields: spec 12) | `ChatResponse` `{ mode, columns, rows, rowCount, truncated, sql, timings, tokens, modelId }` | `chatQueryKey(text)` = `['chat', text]` | `useChat(sent)` — enabled only after a send; `retry: false`, no refetch on focus/reconnect, `staleTime` 60 s (same text within 60 s from the cache), `keepPreviousData` (previous result shown `aria-busy`); `/chat`. When to send (800 ms debounce, ≥ 3 chars, vector mode only; `sql` only on Search/Enter): spec 13, `chat/view.ts` |
| `fetchAuthSession` access token claim `cognito:groups` (Cognito, not the API) | `string[]` | `groupsQueryKey(userId)` = `['groups', userId]` | `useGroups()` (`auth/session.ts`) — Header Admin link, `Profile` role line; see `amplify-auth` |
| `fetchUserAttributes` (Cognito, not the API) | Amplify output | `['user-attributes']` | profile on Home |
| session (`getCurrentUser`) | `Session \| null` | `['auth','session']` | Home, guards, header |

## Pure view logic (unit-tested in Node, no DOM)

- `profile/format.ts` `groupsFromClaims(payload)` (claim absent or malformed → `[]`) and
  `selectRoleLine(status, groups)` — role line per spec 09 (`null` while loading, "Role: unavailable" only when the
  session cannot be read).
- `admin/view.ts` — `selectAdminView` (unconfigured / loading / signing-out / forbidden / error / empty / data),
  `paging` (paging line, Previous/Next), `USER_COLUMNS`, `userCells` (dates `DD/MM/YYYY`, `createdAt` by its UTC
  date, country name + code, `null` → "—", odd values as stored).
- `chat/view.ts` — `chatMode` (`\bsql\b`, case-insensitive), `shouldAutoSend`, `canSubmit`, `chatErrorMessage`,
  `formatCell` (`null` → "—", `distance` 4 decimals), `metaLine`. Results are rendered as React text nodes only.
- Tests: `api/client.test.ts`, `admin/view.test.ts`, `profile/format.test.ts`, `chat/view.test.ts`. Component tests (React Testing
  Library) are not set up — they need the owner's approval of the new dev dependencies.

A later endpoint is added together with its spec: type + path helper + query key in `client.ts`, hook in
`queries.ts` with `retry: retryApi`, and a row in the table above.
