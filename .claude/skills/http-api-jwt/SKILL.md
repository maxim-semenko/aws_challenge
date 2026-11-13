---
name: http-api-jwt
description: How this project uses the HTTP API aws-challenge-api with the Cognito JWT authorizer — authorizer settings, access token per ADR-004 (aud vs client_id), why routes use explicit methods instead of ANY (CORS preflight), CORS settings, how to add a route by console runbook and how to prove the authorizer (401 without token, not 401 with token, preflight 204). Use when writing a runbook that touches the API, routes, authorizer or CORS, when collecting evidence for spec 05, or when planning the Week 3 endpoints.
license: MIT
metadata:
  domain: infrastructure
  triggers: API Gateway, HTTP API, JWT authorizer, cognito-jwt-authorizer, aws-challenge-api, route, ANY, OPTIONS, preflight, CORS, 401, Unauthorized, access token, client_id, aud
  role: specialist
  scope: infrastructure
  related-skills: cloud-architect, cognito-user-pool, spa-api-client
  source: project (created by T02-03)
  used-by: [devops]
---

# HTTP API with Cognito JWT authorizer

Design: [docs/design/api-gateway-auth.md](../../../docs/design/api-gateway-auth.md); ACs: [spec 05](../../../docs/specs/05-protected-api.md).
Identifiers and exact values (API id, endpoint, authorizer id, issuer, audience, routes, CORS):
[docs/ENVIRONMENT.md §HTTP API](../../../docs/ENVIRONMENT.md#http-api-week-2) — **link, never copy**. Built manually
in the console by the owner on 2026-11-13 (T02-03); agents have no AWS access (CLAUDE.md §3.11).

## Authorizer

- Type JWT, identity source `$request.header.Authorization` (`Bearer <token>`).
- Issuer = `https://cognito-idp.<region>.amazonaws.com/<user pool id>`; audience = the SPA app client id. Both from
  the pool ([cognito-user-pool](../cognito-user-pool/SKILL.md)); a new pool means a new issuer here.
- API Gateway checks signature (pool JWKS), `iss`, `exp`/`nbf`, and the audience: against `aud` of an **ID token**
  and `client_id` of an **access token** (access tokens have no `aud`). So **both token types pass** the authorizer.
- The SPA sends the **access token** (ADR-004). Week 2 has no handler; the Week 3 handler must reject
  `token_use != access` with 401 (claims in `requestContext.authorizer.jwt.claims`).
- No authorization scopes on the routes; group checks (`cognito:groups`) are the handler's job (Week 3).
- Rejection body is fixed by HTTP API: 401 `{"message":"Unauthorized"}` (no gateway responses, no problem+json).

## Routes: explicit methods, never `ANY`

Lesson of 2026-11-13: an `ANY /path` route with the JWT authorizer also matches the browser's `OPTIONS` preflight;
the preflight carries no token, so it gets 401 and the browser blocks the real call as a CORS error. API Gateway
answers preflights automatically (204 with CORS headers) only when **no route matches `OPTIONS`**. Therefore every
route is `METHOD /path` with the authorizer (as built: `GET /admin`, `POST /chat`), no `ANY`, no `OPTIONS` route, no
`$default` route, no route without the authorizer.

## CORS (API-level setting)

Allow origin: the Amplify domain only; allow headers `authorization`, `content-type`; credentials off (the token is a
header, not a cookie). Exact values: ENVIRONMENT.md. CORS is not access control — the authorizer is.

## Changing the API (console runbook, owner executes)

Add a route: API Gateway → `aws-challenge-api` → Routes → Create → method + path → attach authorizer
`cognito-jwt-authorizer` → attach integration; stage `$default` auto-deploys. Then update ENVIRONMENT.md and run the
verify steps below. Every change is written first as a runbook in the task Notes (page, field, exact value, what to
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

## Moves to Week 3 (not built)

`/api` prefix and the endpoint contract of CLAUDE.md §6 (problem+json, pagination); the Lambda integration code in
Git (`lambdas/admin`, R-15) with `token_use` and `admin` group checks; access logs and handler log lines (S7);
throttling; invoke permission by `SourceArn`; CORS for `http://localhost:5173` and a non-zero preflight max age.
