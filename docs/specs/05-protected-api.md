# Spec 05 — Protected API: HTTP API, JWT authorizer, `/api/me`, admin probe

Requirements: [week-02](../requirements/week-02-authorization.md) W2-G3, W2-G4, S4, S5, S7 ·
Design: [api-gateway-auth](../design/api-gateway-auth.md)
Tasks: T02-02, T02-03, T02-05, T02-06

## Purpose

Only requests with a valid Cognito access token reach the `admin` Lambda; the caller can read who the API thinks they
are; one route is reserved for the `admin` group; every request is traceable in CloudWatch without tokens or personal
data.

## Inputs

| Name | Type | Valid range | Required |
|---|---|---|---|
| `Authorization` header | string | `Bearer <JWT>` issued by `awsch-dev-users` for app client `awsch-dev-spa`, not expired, `token_use=access` | yes (both routes) |
| `GET /api/me` | request | no body, no query parameters (any are ignored) | — |
| `GET /api/admin/ping` | request | no body, no query parameters (any are ignored) | — |
| `Origin` header | string | `https://main.<appId>.amplifyapp.com` or `http://localhost:5173` for CORS | no |
| Claims used by the handler | from `requestContext.authorizer.jwt.claims` | `sub`, `token_use`, `username`, `exp` (epoch seconds), `cognito:groups` (absent, `[a b]` string or JSON array) | `sub`, `token_use`, `exp` |
| Handler env vars | string | unchanged from the Week 1 build (probe settings, spec 02) | — |

No Week 2 endpoint accepts a request body.

## Outputs

`GET /api/me` → 200 `application/json`:

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` | string | claim `sub` | Cognito user id |
| `username` | string \| null | claim `username` | Cognito internal user name (not the e-mail) |
| `groups` | string[] | claim `cognito:groups` | `[]` when absent |
| `expiresAt` | string | claim `exp` | ISO-8601 UTC, e.g. `2026-11-12T10:15:00Z` |

`GET /api/admin/ping` → 200 `{"status":"ok"}`.

Errors from the handler: `application/problem+json` with `type`, `title`, `status`, `detail` (CLAUDE.md §6):

| Status | When | `detail` (exact) |
|---|---|---|
| 401 | authorizer passed but `token_use ≠ access`, or `sub` / `exp` missing | `Access token required` |
| 403 | `/api/admin/ping` and `admin` not in groups | `Admin group required` |
| 404 | an API event with a `routeKey` the handler does not know | `Route not found` |
| 500 | unexpected error | `Internal error` (no technical detail) |

401 produced by the authorizer (no/invalid/expired token): body `{"message":"Unauthorized"}` (ARCHITECTURE §3.3).

Log lines:

| Source | Fields | Never contains |
|---|---|---|
| API access log `/aws/apigateway/awsch-dev-api` | `requestId`, `routeKey`, `status`, `responseLatency`, `integrationError`, `authorizerError`, `sub` | token, `Authorization` header |
| `admin` handler, one line per API request | `level`, `message`, `awsRequestId`, `apiRequestId`, `userSub`, `routeKey`, `status`, `durationMs` | token, e-mail, names, any profile value |

## Behaviour

1. API Gateway receives the request; for `OPTIONS` preflight it answers from the CORS configuration without the
   authorizer.
2. The JWT authorizer validates signature (JWKS of the pool), `iss`, `exp`/`nbf`, and `aud` (ID token) or `client_id`
   (access token) against the app client id; on failure → 401 without invoking Lambda.
3. The `admin` function receives the payload v2 event and reads the claims; `token_use ≠ access` → 401 problem.
4. `GET /api/me`: builds the response from the claims only; no database or AWS call.
5. `GET /api/admin/ping`: groups parsed from the claim; contains `admin` → 200, else 403. No database or AWS call.
6. The handler writes one log line; `apiRequestId` (`requestContext.requestId`) equals the access-log `requestId`.
7. An event without `requestContext.http` (direct `aws lambda invoke` with `{}`) runs the existing Week 1 probe
   unchanged (spec 02).

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| No `Authorization` header / not `Bearer` | 401 from the authorizer, Lambda not invoked |
| Expired token | 401 from the authorizer |
| Token signed by another pool or for another app client | 401 from the authorizer |
| Tampered payload (signature mismatch) | 401 from the authorizer |
| Valid **ID** token of the right client | passes the authorizer; handler → 401 problem `Access token required` |
| User added to `admin` but token issued before | 403 until the next sign-in/refresh (documented, not a defect) |
| `cognito:groups` as `[admin users]` string or JSON array | both parsed; `admin` found |
| Route not defined (`POST /api/me`, `/api/unknown`) | 404 from API Gateway, Lambda not invoked |
| Preflight from a non-listed origin | no `Access-Control-Allow-Origin` in the response |
| Request rate above the stage throttling limits (ARCHITECTURE §3.3) | 429 from API Gateway |

## Acceptance Criteria

- [ ] AC-05.1 `aws apigatewayv2 get-apis` shows `awsch-dev-api` with `ProtocolType=HTTP`; `get-authorizers` shows one
  JWT authorizer with the pool issuer URL and audience = app client id
- [ ] AC-05.2 `get-routes` shows exactly `GET /api/me` and `GET /api/admin/ping`, each with `AuthorizationType=JWT`;
  no `ANY` or `$default` route
- [ ] AC-05.3 `curl` to both routes without a token, with a malformed token and with an expired token → 401
- [ ] AC-05.4 `GET /api/me` with a valid access token → 200; `id` equals the token's `sub`, `groups` equals its
  `cognito:groups` (or `[]`), `expiresAt` equals its `exp` in ISO-8601 UTC
- [ ] AC-05.5 `GET /api/me` with a valid **ID** token → 401 `application/problem+json`, `detail` = `Access token required`
- [ ] AC-05.6 `GET /api/admin/ping` with a non-admin access token → 403 `application/problem+json`; with an admin
  access token → 200 `{"status":"ok"}`
- [ ] AC-05.7 Preflight `OPTIONS /api/me` with `Origin` = the Amplify domain → `Access-Control-Allow-Origin` equals
  that origin; with `Origin: https://example.com` → header absent
- [ ] AC-05.8 The access log group exists with retention 14 days and contains a JSON line for each call of AC-05.3/05.4
  with `status` and `requestId`; the `admin` log line for the AC-05.4 call has the same `apiRequestId` and a `userSub`
- [ ] AC-05.9 A search of both log groups for the string `eyJ` (JWT prefix) and for the test user's e-mail finds nothing
- [ ] AC-05.10 `aws lambda invoke --function-name awsch-dev-admin` with `{}` returns the same probe result as before
  the deploy (recorded in T02-03 Notes)
- [ ] AC-05.11 The Lambda resource policy of `awsch-dev-admin` allows `apigateway.amazonaws.com` only with `SourceArn`
  of `awsch-dev-api`; the role of `awsch-dev-admin` has no permission added in Week 2
- [ ] AC-05.12 pytest unit tests of the handler cover: `token_use` check, missing claims, group parsing (absent,
  string form, JSON array), 200/401/403/404 mapping, the problem+json body and the `{}` probe dispatch
