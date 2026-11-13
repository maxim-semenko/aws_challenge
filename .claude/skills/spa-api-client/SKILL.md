---
name: spa-api-client
description: How the SPA in frontend/ calls the protected HTTP API — base URL from VITE_API_URL, the Cognito access token in the Authorization header, error handling by status and the TanStack Query keys. Use when adding or changing an API call in frontend/src/api or a page that reads API data.
license: MIT
metadata:
  domain: frontend
  triggers: API client, fetch, VITE_API_URL, Authorization, Bearer, access token, /api/me, TanStack Query, queryKey
  role: specialist
  scope: implementation
  related-skills: react-expert, amplify-auth
  source: project (created by T02-05, partial — the API part is verified after T02-03)
  used-by: [frontend]
---

# SPA API client

Conventions: CLAUDE.md §6. Endpoint fields: [spec 05](../../../docs/specs/05-protected-api.md) §Outputs (single home).

## Client (`frontend/src/api/client.ts`)

- Base URL: `env.apiUrl` from `VITE_API_URL` (trailing `/` removed, no default). The Vite dev proxy to `:8080` was
  removed (ADR-015: no local backend). With an empty `env.apiUrl` the SPA makes **no** API request: the component
  that calls the API is not mounted (Home: no role line; `/chat`, `/admin`: "Not available yet"; owner decision
  2026-11-13).
- Token: `fetchAuthSession()` → `tokens.accessToken` → `Authorization: Bearer <access token>` (ADR-004; the JWT
  authorizer/handler reject the ID token). Amplify refreshes expired tokens inside `fetchAuthSession()`. Never log the
  header or the token.
- Errors: non-2xx → `ApiError(status)`. 401 on a signed-in page → `useSignOut()` (session cleared, `/sign-in`, spec 04);
  401 is not retried. 5xx / network → the page's unavailable state; one retry (QueryClient default).

## Types and query keys

| Endpoint | Type | Query key | Used by |
|---|---|---|---|
| `GET /api/me` | `MeResponse` `{ id, username, groups, expiresAt }` (spec 05) | `meQueryKey` = `['me']` | role line of the profile on Home (`profile/Profile.tsx`) |
| `fetchUserAttributes` (Cognito, not the API) | Amplify output | `['user-attributes']` | profile on Home |
| session (`getCurrentUser`) | `Session \| null` | `['auth','session']` | Home, guards, header |

Other draft endpoints (`health`, `search`, `users`) are drafts from before the plan and not part of any spec yet;
`health` is no longer called (the Home draft was removed 2026-11-13).
