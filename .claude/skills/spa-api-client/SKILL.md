---
name: spa-api-client
description: How the SPA in frontend/ calls the protected HTTP API — base URL from VITE_API_URL, the Cognito access token in the Authorization header, error handling by status (401 sign-out, 403 no-access, retry rule) and the TanStack Query keys. Use when adding or changing an API call in frontend/src/api or a page that reads API data.
license: MIT
metadata:
  domain: frontend
  triggers: API client, fetch, VITE_API_URL, Authorization, Bearer, access token, /api/me, /api/admin/users, TanStack Query, queryKey, 403, paging
  role: specialist
  scope: implementation
  related-skills: react-expert, amplify-auth
  source: project (created by T02-05; endpoints, query keys and 403 handling updated by T03-08)
  used-by: [frontend]
---

# SPA API client

Conventions: CLAUDE.md §6. Endpoint fields: [spec 08](../../../docs/specs/08-admin-api.md) §Outputs (single home);
UI states and texts: [spec 09](../../../docs/specs/09-admin-page-and-role.md).

## Client (`frontend/src/api/client.ts`)

- Base URL: `env.apiUrl` from `VITE_API_URL` (trailing `/` removed, no default). No local backend (ADR-015).
- `isApiConfigured` (`config/amplify.ts`) = `VITE_API_URL` set **and** auth configured (every route needs a token).
  Without it the SPA makes **no** API request: the components that call the API are not mounted (`Profile` role
  line, `AdminPage` shows the `ComingLater` placeholder) and `useMe` is disabled (AC-04.10). `/chat` stays a
  placeholder without request until Week 5.
- Token: `fetchAuthSession()` → `tokens.accessToken` → `Authorization: Bearer <access token>` (ADR-004; the handler
  rejects the ID token). Amplify refreshes expired tokens inside `fetchAuthSession()`. Never log the header or token.
- Errors: non-2xx → `ApiError(status)` (the problem+json body is not parsed; the UI texts come from spec 09).
  Network failure → the `fetch` `TypeError`.
- Retry rule `retryApi`: 4xx never retried (401, 403, 400, 404, 429); 5xx and network errors retried once. Every
  API query sets `retry: retryApi`.

## Status handling

| Status | Behaviour |
|---|---|
| 401 | `useSignOutOnUnauthorized(error)` (`api/queries.ts`) → `useSignOut()` (cache cleared, `/sign-in`). Called once per query: Header for `['me']`, `AdminPage` for the users list |
| 403 | page-specific no-access state (`/admin`: "You do not have access to this page."), no table |
| 5xx / network | unavailable state (role line "Role: unavailable"; `/admin` "Users could not be loaded." + Retry); an error always wins over placeholder data |

## Endpoints, types and query keys

| Endpoint | Type | Query key | Hook / used by |
|---|---|---|---|
| `GET /api/me` | `MeResponse` `{ id, username, groups, expiresAt }` | `meQueryKey` = `['me']` | `useMe()` — enabled with `isApiConfigured` and a session, `staleTime: Infinity` (once per session; dropped by sign-out); Header (Admin link only if `groups` contains `admin`, display only), `Profile` role line |
| `GET /api/admin/users?page=<p>&size=20` (default sort, no `sort` param) | `Page<User>` `{ items, page, size, total }` | `adminUsersQueryKey(p)` = `['admin','users',p]` | `useAdminUsers(page)` — `placeholderData: keepPreviousData` (previous page visible while the next loads; paging buttons disabled meanwhile); `/admin` |
| `fetchUserAttributes` (Cognito, not the API) | Amplify output | `['user-attributes']` | profile on Home |
| session (`getCurrentUser`) | `Session \| null` | `['auth','session']` | Home, guards, header |

## Pure view logic (unit-tested in Node, no DOM)

- `profile/format.ts` `selectRoleLine(status, groups, errorStatus)` — role line per spec 09 (`null` while loading or
  signing out on 401).
- `admin/view.ts` — `selectAdminView` (unconfigured / loading / signing-out / forbidden / error / empty / data),
  `paging` (paging line, Previous/Next), `USER_COLUMNS`, `userCells` (dates `DD/MM/YYYY`, `createdAt` by its UTC
  date, country name + code, `null` → "—", odd values as stored).
- Tests: `api/client.test.ts`, `admin/view.test.ts`, `profile/format.test.ts`. Component tests (React Testing
  Library) are not set up — they need the owner's approval of the new dev dependencies.

A later endpoint is added together with its spec: type + path helper + query key in `client.ts`, hook in
`queries.ts` with `retry: retryApi`, and a row in the table above.
