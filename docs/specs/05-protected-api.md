# Spec 05 — Protected API: HTTP API with a Cognito JWT authorizer

Requirements: [week-02](../requirements/week-02-authorization.md) W2-G3, S4 ·
Design: [api-gateway-auth](../design/api-gateway-auth.md)
Tasks: T02-03, T02-06

Reduced 2026-11-13 (owner: Week 2 = the curriculum topic only). **Moved to Week 3** and specified there: the `admin`
Lambda code in Git, `GET /api/me`, `GET /api/admin/ping`, the `admin` group check (403), the `token_use` check, the
handler's `application/problem+json` errors, the role line in the SPA, the API access log and the log-content checks.

Week 3 ([spec 08](08-admin-api.md), ADR-018, owner 2026-11-17): the routes `GET /admin` and `POST /chat` stay (the
curriculum diagram's routes; the 2026-11-13 plan to replace them with `/api/...` routes is withdrawn); `GET /admin`
gets its contract in spec 08 (AC-08.3 adds the integration check); the authorizer behaviour (AC-05.1 … AC-05.6)
still applies.

## Purpose

The HTTP API `aws-challenge-api`, built by the owner in the console, is the only public door to the functions: a
request without a valid Cognito token of the pool `aws-challenge-users` / app client `aws-challenge-frontend-spa` is
rejected by API Gateway with 401 before any integration runs, a request with a valid access token reaches the route's
integration, and the SPA origin passes the CORS preflight. What the integrations return is not part of Week 2.

## Inputs

| Name | Type | Valid range | Required |
|---|---|---|---|
| Route | request | `GET /admin`, `POST /chat` as built ([ENVIRONMENT.md](../ENVIRONMENT.md#http-api-week-2)) | — |
| `Authorization` header | string | `Bearer <JWT>` issued by `aws-challenge-users` for app client `aws-challenge-frontend-spa`, not expired; the SPA uses the access token (ADR-004) | yes |
| `Origin` header | string | the Amplify origin recorded in ENVIRONMENT.md for CORS | no |

No request body or query parameter is defined in Week 2.

## Outputs

| Case | Response |
|---|---|
| Authorizer rejects the request | 401, body `{"message":"Unauthorized"}` (fixed HTTP API body, ARCHITECTURE §3.3); no integration invoked |
| Authorizer accepts the request | the response of the route's integration; status and body not specified in Week 2 (only "not 401") |
| CORS preflight from the Amplify origin | 2xx answered by API Gateway with `Access-Control-Allow-Origin` = that origin |

## Behaviour

1. API Gateway receives the request; an `OPTIONS` preflight is answered from the API's CORS configuration without the
   authorizer.
2. The JWT authorizer `cognito-jwt-authorizer` reads `$request.header.Authorization` and validates the signature
   (JWKS of the pool), `iss`, `exp`/`nbf`, and `aud` (ID token) or `client_id` (access token) against the app client
   id; on failure → 401 without invoking the integration.
3. On success API Gateway invokes the route's integration (payload format as built); what it does with the request is
   Week 3.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| No `Authorization` header / not a JWT (`Bearer abc`) | 401 from the authorizer |
| Expired access token | 401 from the authorizer |
| Token signed by another pool, or for another app client | 401 from the authorizer |
| Tampered token (signature mismatch) | 401 from the authorizer |
| Valid **ID** token of the same app client | passes the authorizer as well (ADR-004); rejecting `token_use ≠ access` is the Week 3 handler's job — known, not a Week 2 defect |
| Path without a route (e.g. `/unknown`) | 404 from API Gateway |
| Preflight from a non-listed origin (e.g. `https://example.com`) | no `Access-Control-Allow-Origin` in the response |
| Preflight from `http://localhost:5173` | not allowed (origin not listed as built); no Week 2 screen calls the API, revisited in Week 3 |

## Acceptance Criteria

AWS-side criteria are verified from evidence the owner provides (console screenshots; status codes from the browser
console or Network tab of the deployed SPA, or from `curl`); agents have no AWS access (CLAUDE.md §3.11). Token
values never appear in the evidence.

- [ ] AC-05.1 The API `aws-challenge-api` exists with protocol HTTP, stage `$default` and the JWT authorizer
  `cognito-jwt-authorizer` with identity source `$request.header.Authorization`, issuer = the pool issuer URL and
  audience = the app client id (values in ENVIRONMENT.md)
- [ ] AC-05.2 The routes are `GET /admin` and `POST /chat` (no `ANY` route: it would capture the CORS preflight), each with authorization type JWT and this authorizer; there
  is no route without the authorizer and no `$default` route
- [ ] AC-05.3 A request to `/admin` and to `/chat` without an `Authorization` header → 401
- [ ] AC-05.4 A request to `/admin` with each of: `Authorization: Bearer abc`, a valid access token with one character
  of its signature changed, an access token older than 60 minutes (expired) → 401
- [ ] AC-05.5 A request to `/admin` and to `/chat` with a valid access token of a signed-in user of the deployed SPA
  → status not 401 (the request passed the authorizer; the status returned by each integration is recorded)
- [ ] AC-05.6 A CORS preflight (`OPTIONS`, `Origin` = the Amplify origin, `Access-Control-Request-Method: GET`,
  `Access-Control-Request-Headers: authorization`) to `/admin` → 2xx with `Access-Control-Allow-Origin` equal to that
  origin
