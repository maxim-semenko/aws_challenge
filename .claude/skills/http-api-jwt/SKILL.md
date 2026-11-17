---
name: http-api-jwt
description: How this project uses the HTTP API aws-challenge-api with the Cognito JWT authorizer — authorizer settings, access token per ADR-004 (aud vs client_id), the two routes of the curriculum diagram (GET /admin, POST /chat; ADR-018, no /api prefix), why routes use explicit methods instead of ANY (CORS preflight), payload 2.0 integration and invoke permission, CORS settings, how to change a route by console runbook and how to prove the authorizer (401 without token, preflight 204). Use when writing a runbook that touches the API, routes, authorizer or CORS, or when collecting evidence for spec 05 or spec 08.
license: MIT
metadata:
  domain: infrastructure
  triggers: API Gateway, HTTP API, JWT authorizer, cognito-jwt-authorizer, aws-challenge-api, route, ANY, OPTIONS, preflight, CORS, 401, Unauthorized, access token, client_id, aud
  role: specialist
  scope: infrastructure
  related-skills: cloud-architect, cognito-user-pool, spa-api-client
  source: project (created by T02-03, updated by T03-07)
  used-by: [devops]
---

# HTTP API with Cognito JWT authorizer

Design: [docs/design/api-gateway-auth.md](../../../docs/design/api-gateway-auth.md) (Week 2),
[docs/design/admin-api.md](../../../docs/design/admin-api.md) §3 (Week 3); ACs: [spec 05](../../../docs/specs/05-protected-api.md),
[spec 08](../../../docs/specs/08-admin-api.md) AC-08.3, AC-08.4, AC-08.8.
Identifiers and exact values (API id, endpoint, authorizer id, issuer, audience, routes, CORS):
[docs/ENVIRONMENT.md §HTTP API](../../../docs/ENVIRONMENT.md#http-api-week-2) — **link, never copy**. Built manually
in the console by the owner on 2026-11-13 (T02-03); agents have no AWS access (CLAUDE.md §3.11).

## Authorizer

- Type JWT, identity source `$request.header.Authorization` (`Bearer <token>`).
- Issuer = `https://cognito-idp.<region>.amazonaws.com/<user pool id>`; audience = the SPA app client id. Both from
  the pool ([cognito-user-pool](../cognito-user-pool/SKILL.md)); a new pool means a new issuer here.
- API Gateway checks signature (pool JWKS), `iss`, `exp`/`nbf`, and the audience: against `aud` of an **ID token**
  and `client_id` of an **access token** (access tokens have no `aud`). So **both token types pass** the authorizer.
- The SPA sends the **access token** (ADR-004). The `admin` handler rejects `token_use != access` with 401 (claims in
  `requestContext.authorizer.jwt.claims`; admin-api skill).
- No authorization scopes on the routes; the group check (`cognito:groups`) is the handler's job.
- Rejection body is fixed by HTTP API: 401 `{"message":"Unauthorized"}` (no gateway responses, no problem+json).

## Routes: exactly the curriculum diagram (ADR-018)

| Route | Integration | Contract |
|---|---|---|
| `GET /admin` | Lambda `aws-challenge-admin`, **payload format 2.0** (the handler routes on `routeKey`) | users list for the group `admin` — spec 08 |
| `POST /chat` | chatbot integration (Week 5) | none until Week 5 |

No `/api` prefix and no other route (a new route needs an ADR, CLAUDE.md §6). The `/api/me` and `/api/admin/users`
routes of the 2026-11-13 design were created and deleted on 2026-11-17; they answer 404. The SPA reads the role from
the access token, not from the API. Invoke permission: the `aws-challenge-admin` resource policy allows
`apigateway.amazonaws.com` only with a `SourceArn` of this API (e.g. `…:<api id>/*/*/admin`).

## Routes: explicit methods, never `ANY`

Lesson of 2026-11-13: an `ANY /path` route with the JWT authorizer also matches the browser's `OPTIONS` preflight;
the preflight carries no token, so it gets 401 and the browser blocks the real call as a CORS error. API Gateway
answers preflights automatically (204 with CORS headers) only when **no route matches `OPTIONS`**. Therefore every
route is `METHOD /path` with the authorizer (as built: `GET /admin`, `POST /chat`), no `ANY`, no `OPTIONS` route, no
`$default` route, no route without the authorizer.

## CORS (API-level setting)

Allow origins: the Amplify domain and `http://localhost:5173` (local development, Week 3); allow headers
`authorization`, `content-type`; max age 600 s; credentials off (the token is a header, not a cookie). Exact values:
ENVIRONMENT.md. CORS is not access control — the authorizer is.

## Changing the API (console runbook, owner executes)

Change a route (only with an ADR): API Gateway → `aws-challenge-api` → Routes → method + path → attach authorizer
`cognito-jwt-authorizer` → attach integration (Lambda, payload 2.0); stage `$default` auto-deploys. Then update
ENVIRONMENT.md and run the verify steps below. Every change is written first as a runbook in the task Notes (page, field, exact value, what to
report back). IaC later (T00-03, Q-02).

## Verify (spec 05; status codes only, never print or screenshot a token)

- `curl -i <endpoint>/admin` (no `Authorization`) → 401; same with `Authorization: Bearer abc` and with a forged JWT
  → 401.
- Preflight: `curl -i -X OPTIONS <endpoint>/admin -H "Origin: <amplify origin>" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization"`
  → 204 with `access-control-allow-origin: <amplify origin>`.
- With a token: browser DevTools console on the deployed, signed-in SPA, `fetch` with the access token from Amplify's
  `localStorage` → anything but 401 (snippet in [T02-03](../../../docs/tasks/P2-authorization/T02-03-http-api-jwt.md)
  Notes). No token in shell history (`curl` with a copied token is avoided).
- Expired token → 401 (needs a session older than the access token validity).

- Week 3 (spec 08): `GET /admin` and `POST /chat` without a token → 401, `/api/me` → 404; preflight
  `OPTIONS /admin` → 204 with `access-control-max-age: 600`; with the admin's token `GET /admin?page=0&size=2` → 200,
  with a non-admin's → 403 problem+json (snippet in T03-07 step 6).

## Deferred to Week 6 (owner, 2026-11-17)

API access log (JSON, `requestId` = handler `apiRequestId`) and stage throttling (50 rps / burst 100) — target in
ARCHITECTURE §3.3; not built.
