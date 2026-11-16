# Design — Admin API and admin page (Admin Lambda ↔ RDS Proxy, `/api` endpoints, group `admin`)

Status: **Accepted** (owner, 2026-11-13). Decisions: [Q-18](../RISKS.md#q-18) A (database access, shared with
[user-sync](user-sync.md)) and [Q-19](../RISKS.md#q-19) A (personal page source), owner 2026-11-13; the proposed
solution below is the accepted one.
Requirements: [week-03](../requirements/week-03-rest-api-data.md) W3-G2, W3-G3, W3-G4, W3-G5, S3, S4, S6, S7, S8 ·
Specs: [08-admin-api](../specs/08-admin-api.md), [09-admin-page-and-role](../specs/09-admin-page-and-role.md)
Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md) §3.3, §5.2, §6, §9, ADR-003, ADR-004, ADR-013, ADR-015, goals
G4, G5, G8
Related design: [api-gateway-auth](api-gateway-auth.md) (Week 2 API, "Moved to Week 3" list),
[authentication](authentication.md) (SPA, Cognito), [user-sync](user-sync.md) (table, DB access)

## Problem Statement

The administrator must see all users and their data in a read-only table with paging; every user must see the own
role on the personal page (requirements). The Week 2 API has only `GET /admin` and `POST /chat` without a contract,
the `admin` Lambda code exists only in the console (R-15), there is no group `admin`, no `token_use` or group check,
no problem+json errors and no API access log (all moved from Week 2). "REST API" in the curriculum is read as the API
style; the product stays the HTTP API (ADR-003).

## Proposed Solution

```mermaid
sequenceDiagram
    participant B as SPA (signed in)
    participant G as HTTP API aws-challenge-api<br/>JWT authorizer
    participant A as Lambda admin (VPC)
    participant P as RDS Proxy → PostgreSQL
    B->>G: GET /api/me (Bearer access token)
    G->>A: payload v2 + jwt claims
    A-->>B: 200 {id, username, groups, expiresAt} (claims only)
    B->>G: GET /api/admin/users?page=0&size=20
    G->>A: claims (cognito:groups)
    A->>A: token_use = access? group admin? query params valid?
    A->>P: SELECT count(*); SELECT … ORDER BY … LIMIT/OFFSET (IAM token, TLS)
    A-->>B: 200 {items, page, size, total} | 400/401/403 problem+json
```

### 1. Group `admin`

Created by the owner in the Cognito console (no IAM role, no precedence needed); the owner adds his own account.
Membership arrives in the access token as `cognito:groups` after the next sign-in (or token refresh, ≤ 60 min).
Members are managed only by the owner in the console.

### 2. Admin Lambda (`aws-challenge-admin`, code `lambdas/admin/`)

- Python 3.12 (ADR-015 revised 2026-11-16), VPC as built, timeout 10 s, memory 256 MB; DB access per [user-sync](user-sync.md) §1 (IAM auth to
  the proxy, env `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_USER`). The Week 1 direct-invoke probe is dropped (the API
  proves the connection).
- Router on `event.routeKey` (payload v2): `GET /api/me`, `GET /api/admin/users`; anything else → 404 problem+json
  (defensive; API Gateway already returns 404 for unknown routes).
- Checks, in this order: claims present and `token_use == "access"` (else 401, ADR-004) → route → for `/api/admin/*`
  `"admin"` in `cognito:groups` (else 403) → query parameters (else 400) → database.
- `cognito:groups` arrives in the payload-v2 claims as a string (e.g. `[admin]` or `admin`), not a JSON array: the
  handler parses both forms (re-check the exact format in the first deployed log line; spec 08 Edge Cases).
- `GET /api/me` (Q-19 A): no database call; identity, groups and token expiry from the claims.
- `GET /api/admin/users`: two parameterised statements (`count(*)`, page query with `ORDER BY <whitelisted column>
  <asc|desc>, id` and `LIMIT/OFFSET`); sort column mapped from a fixed dict, never interpolated from input.
- Errors: RFC 9457 `application/problem+json` from the handler for 400, 401 (`token_use`), 403, 404, 500. Database
  failures → 500 with a generic `detail` (no SQL, no host). Fixed API Gateway bodies remain for the authorizer 401
  and unknown-route 404 (ARCHITECTURE §3.3 exception).
- One JSON log line per request (fields in spec 08): correlation `awsRequestId`, `apiRequestId`
  (`requestContext.requestId`), `userSub`; route, status, duration, outcome; never the token or user data.

### 3. HTTP API changes (owner, console runbook)

| Item | Change |
|---|---|
| Routes | **add** `GET /api/me`, `GET /api/admin/users` (JWT authorizer, Lambda integration `aws-challenge-admin`, payload 2.0); **delete** `GET /admin` and `POST /chat` (no contract; Week 5 adds `POST /api/chat/search`). Explicit methods only, no `ANY`, no `$default` (http-api-jwt skill) |
| Invoke permission | Lambda resource policy for `apigateway.amazonaws.com` scoped by `SourceArn` to this API's `/api/*` routes |
| Access log | stage `$default` → log group `/aws/apigateway/aws-challenge-api`, retention 14 days, JSON format of spec 08 (no source IP, no user agent) |
| Throttling | stage default route throttling: rate 50 rps, burst 100 (ARCHITECTURE §3.3) |
| CORS | add origin `http://localhost:5173` (local development against the dev API); max age 600 s; rest unchanged |

### 4. SPA (`frontend/`)

| Element | Behaviour |
|---|---|
| Role line on the profile card | from `GET /api/me` `groups`: "Role: administrator" / "Role: user"; "Role: unavailable" on 5xx/network; not rendered without `VITE_API_URL` |
| Admin nav link | shown only to a signed-in user whose `/api/me` groups contain `admin` (display only — the API enforces) |
| `/admin` page | admin: read-only table of users with paging (page size 20, Previous / Next, "Page n of m", total); non-admin: "You do not have access to this page." (from 403); empty table: "No users yet."; without `VITE_API_URL`: the existing "Not available yet" placeholder (spec 04 AC-04.10) |
| Chat | unchanged placeholder (Week 5) |

Columns, formats and states: [spec 09](../specs/09-admin-page-and-role.md). Profile values stay from Cognito
(Q-19 A, ADR-013 unchanged).

## Alternatives Considered

| Topic | Option | Pros | Cons | Verdict |
|---|---|---|---|---|
| API product | HTTP API (ADR-003) | built, JWT native, cheaper | no request validation | **kept** ("REST" = style) |
| API product | REST API | curriculum word literally | rebuild, ~3.5× price | rejected |
| Group check | in the handler from `cognito:groups` | works with the access token | code per route | **recommended** |
| Group check | authorization scopes on the route | at the edge | needs a resource server + OAuth scopes; the SRP flow issues no custom scopes | rejected |
| Group check | Lambda authorizer | central | another function, cache, latency | rejected |
| `/api/me` content (Q-19) | A: claims only | no DB dependency, role line works if sync lags | profile from Cognito | **recommended** |
| `/api/me` content (Q-19) | B: DB row | one read path | "not synced" state, drift | alternative |
| `/api/admin/ping` | keep (from the Week 2 plan) | trivial 403 proof | `/api/admin/users` proves the same | dropped |
| Old routes | delete `GET /admin`, `POST /chat` | API surface = contract; §6 `/api` prefix | Week 5 recreates a chat route | **recommended** |
| Old routes | keep them | nothing to change | routes without contract stay public-facing | rejected |
| Paging | `LIMIT/OFFSET` + `count(*)` | matches §6 `{items,page,size,total}`; fine for ≤ thousands | deep pages slower | **recommended** |
| Paging | keyset | stable, fast | no `total`/`page` semantics of §6 | rejected |
| Admin link | from `/api/me` groups | one source for the role | one request per session | **recommended** |
| Admin link | from the access token payload in the SPA | no request | second source of the role | rejected |
| Logging | stdlib JSON line now, Powertools in Week 6 (ADR-012) | no dependency now | rework in Week 6 | **recommended** |
| Logging | Powertools Logger now | final form | pulls Week 6 forward; R-10 unresolved | rejected |

## API Design

Conventions: CLAUDE.md §6. Field-level contract: [spec 08](../specs/08-admin-api.md) §Inputs/§Outputs.

| Method | Path | Auth | Parameters | 200 response | Errors |
|---|---|---|---|---|---|
| GET | `/api/me` | JWT (access token) | none | `{ id, username, groups, expiresAt }` | 401 |
| GET | `/api/admin/users` | JWT + group `admin` | `page` (≥ 0, default 0), `size` (1..100, default 20), `sort` (`createdAt\|email\|familyName`,`asc\|desc`; default `createdAt,desc`) | `{ items: User[], page, size, total }` | 400, 401, 403, 500 |

No endpoint creates or updates data (requirements: no editing). Unknown query parameters → 400.

## Affected Components

- **AWS (owner, runbooks):** Cognito group `admin` + membership (T03-01); `aws-challenge-admin` configuration, role
  and code upload (T03-07); API routes, permission, access log, throttling, CORS (T03-07).
- **Repository:** `lambdas/admin/` (handler + pytest, T03-06); `frontend/src` API client types, profile role line,
  header, admin page (T03-08).
- **Skills:** `cognito-user-pool` (group, T03-01), `python-lambda` (API handler section, T03-06), `http-api-jwt`
  (routes, access log, T03-07), `spa-api-client` (endpoints, T03-08).
- **Docs:** ENVIRONMENT.md (routes, log group), ARCHITECTURE §3.3, §6; spec 05 note (routes superseded).

## Security Considerations

- Authentication at the edge (JWT authorizer, unchanged); the handler additionally rejects ID tokens
  (`token_use`), which pass the authorizer (ADR-004).
- Authorisation in the handler: only group `admin` reads other users' data; the SPA's hidden link is cosmetic.
- Claims are read only from `requestContext.authorizer.jwt.claims`, never from headers or query.
- Input: `page`, `size`, `sort` validated against the spec; sort column from a whitelist; parameterised SQL.
- The users list returns personal data to admins only; responses carry no caching headers that allow shared caches
  (`Cache-Control: no-store`).
- Logs: no token, no e-mail or profile values; access log without source IP and user agent (CLAUDE.md §7).
- Throttling bounds abuse and cost; CORS lists only the Amplify origin and localhost (CORS is not access control).
- DB user shared across functions: R-16 (accepted for Week 3).

## Cost

No always-on resources. HTTP API about $1 per million requests; CloudWatch Logs ingestion and storage for the access
log within the learning volume ≈ $0 (eu-west-1 price per GB, re-check). Database access per
[user-sync](user-sync.md) §Cost.

## Open Questions

None open. Answered by the owner on 2026-11-13:

| ID | Question | Decision |
|---|---|---|
| [Q-18](../RISKS.md#q-18) | DB credentials / network path (shared with user-sync) | A — IAM auth to RDS Proxy (ADR-006 revised) |
| [Q-19](../RISKS.md#q-19) | Personal page source; content of `GET /api/me` | A — Cognito profile; `/api/me` from claims |
