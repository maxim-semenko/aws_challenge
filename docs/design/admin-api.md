# Design — Admin API and admin page (Admin Lambda ↔ RDS Proxy, route `GET /admin`, group `admin`)

Status: **Accepted** (owner, 2026-11-13; amended 2026-11-17 by the owner: routes as in the curriculum diagram —
ADR-018). Decisions: [Q-18](../RISKS.md#q-18) A (database access, shared with [user-sync](user-sync.md)) and
[Q-19](../RISKS.md#q-19) A (personal page source), owner 2026-11-13; route set and role source: ADR-018, owner
2026-11-17. The proposed solution below is the accepted one.
Requirements: [week-03](../requirements/week-03-rest-api-data.md) W3-G2, W3-G3, W3-G4, W3-G5, S3, S4, S6, S7, S8 ·
Specs: [08-admin-api](../specs/08-admin-api.md), [09-admin-page-and-role](../specs/09-admin-page-and-role.md)
Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md) §3.3, §5.2, §6, §9, ADR-003, ADR-004, ADR-013, ADR-015, ADR-018,
goals G4, G5, G8
Related design: [api-gateway-auth](api-gateway-auth.md) (Week 2 API, "Moved to Week 3" list),
[authentication](authentication.md) (SPA, Cognito), [user-sync](user-sync.md) (table, DB access)

## Problem Statement

The administrator must see all users and their data in a read-only table with paging; every user must see the own
role on the personal page (requirements). The Week 2 API has the routes of the curriculum diagram, `GET /admin` and
`POST /chat`, without a contract; the `admin` Lambda code exists only in the console (R-15), there is no group
`admin`, no `token_use` or group check and no problem+json errors (all moved from Week 2). "REST API" in the
curriculum is read as the API style; the product stays the HTTP API (ADR-003).

## Proposed Solution

```mermaid
sequenceDiagram
    participant B as SPA (signed in)
    participant G as HTTP API aws-challenge-api<br/>JWT authorizer
    participant A as Lambda admin (VPC)
    participant P as RDS Proxy → PostgreSQL
    B->>B: role = cognito:groups of the access token (no API call)
    B->>G: GET /admin?page=0&size=20 (Bearer access token)
    G->>A: payload v2 + jwt claims (cognito:groups)
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
- Router on `event.routeKey` (payload v2): only `GET /admin`; anything else → 404 problem+json (defensive; API
  Gateway already returns 404 for unknown routes, and `POST /chat` is integrated with `chatbot`).
- Checks, in this order: claims present and `token_use == "access"` (else 401, ADR-004) → route → `"admin"` in
  `cognito:groups` (else 403) → query parameters (else 400) → database.
- `cognito:groups` arrives in the payload-v2 claims as a string (e.g. `[admin]` or `admin`), not a JSON array: the
  handler parses both forms (re-check the exact format in the first deployed log line; spec 08 Edge Cases).
- `GET /admin`: two parameterised statements (`count(*)`, page query with `ORDER BY <whitelisted column>
  <asc|desc>, id` and `LIMIT/OFFSET`); sort column mapped from a fixed dict, never interpolated from input.
- Errors: RFC 9457 `application/problem+json` from the handler for 400, 401 (`token_use`), 403, 404, 500. Database
  failures → 500 with a generic `detail` (no SQL, no host). Fixed API Gateway bodies remain for the authorizer 401
  and unknown-route 404 (ARCHITECTURE §3.3 exception).
- One JSON log line per request (fields in spec 08): correlation `awsRequestId`, `apiRequestId`
  (`requestContext.requestId`), `userSub`; route, status, duration, outcome; never the token or user data.

### 3. HTTP API changes (owner, console runbook)

| Item | Change |
|---|---|
| Routes | exactly `GET /admin` (JWT authorizer, Lambda integration `aws-challenge-admin`, payload 2.0) and `POST /chat` (JWT authorizer, chatbot integration unchanged until Week 5) — ADR-018. The `/api/...` routes the owner created on 2026-11-17 are deleted. Explicit methods only, no `ANY`, no `$default` (http-api-jwt skill) |
| Invoke permission | Lambda resource policy of `aws-challenge-admin`: `apigateway.amazonaws.com` only with a `SourceArn` of this API (the `GET /admin` route or `/*/*/admin`) |
| CORS | add origin `http://localhost:5173` (local development against the dev API); max age 600 s; rest unchanged |
| Access log, throttling | **deferred to Week 6** (owner, 2026-11-17); target in ARCHITECTURE §3.3 |

### 4. SPA (`frontend/`)

| Element | Behaviour |
|---|---|
| Role line on the profile card | from `cognito:groups` of the current access token (Amplify session, no API call): "Role: administrator" / "Role: user" |
| Admin nav link | shown only to a signed-in user whose access token `cognito:groups` contain `admin` (display only — the API enforces) |
| `/admin` page | admin: read-only table of users with paging from `GET /admin` (page size 20, Previous / Next, "Page n of m", total); non-admin: "You do not have access to this page." (from 403); empty table: "No users yet."; without `VITE_API_URL`: the existing "Not available yet" placeholder (spec 04 AC-04.10) |
| Chat | unchanged placeholder (Week 5) |

Columns, formats and states: [spec 09](../specs/09-admin-page-and-role.md). Profile values stay from Cognito
(Q-19 A, ADR-013 unchanged).

## Alternatives Considered

| Topic | Option | Pros | Cons | Verdict |
|---|---|---|---|---|
| API product | HTTP API (ADR-003) | built, JWT native, cheaper | no request validation | **kept** ("REST" = style) |
| API product | REST API | curriculum word literally | rebuild, ~3.5× price | rejected |
| Route set (ADR-018) | A: `GET /admin`, `POST /chat` as in the curriculum diagram | matches the diagram and the as-built API; nothing extra to build | no `/api` prefix; `/admin` is both an SPA page and an API path (different hosts) | **accepted** (owner, 2026-11-17) |
| Route set (ADR-018) | B: `GET /api/me`, `GET /api/admin/users` (2026-11-13 design) | CLAUDE.md §6 style of the time; role from the server | routes beyond the diagram; one extra request per session | superseded |
| Route set (ADR-018) | C: `GET /admin` + `GET /api/me` | role from the server | two path styles; still beyond the diagram | rejected |
| Role source | access token `cognito:groups` in the SPA | no request; works without the database | display only; stale until refresh (same as any token claim) | **accepted** (with ADR-018) |
| Role source | API endpoint (`/api/me`) | one server-side source | a route not in the diagram | rejected |
| Group check | in the handler from `cognito:groups` | works with the access token | code per route | **recommended** |
| Group check | authorization scopes on the route | at the edge | needs a resource server + OAuth scopes; the SRP flow issues no custom scopes | rejected |
| Group check | Lambda authorizer | central | another function, cache, latency | rejected |
| Paging | `LIMIT/OFFSET` + `count(*)` | matches §6 `{items,page,size,total}`; fine for ≤ thousands | deep pages slower | **recommended** |
| Paging | keyset | stable, fast | no `total`/`page` semantics of §6 | rejected |
| Access log, throttling | Week 3 | S8 traceability now | more console work this week | deferred to Week 6 (owner, 2026-11-17) |
| Logging | stdlib JSON line now, Powertools in Week 6 (ADR-012) | no dependency now | rework in Week 6 | **recommended** |
| Logging | Powertools Logger now | final form | pulls Week 6 forward; R-10 unresolved | rejected |

## API Design

Conventions: CLAUDE.md §6. Field-level contract: [spec 08](../specs/08-admin-api.md) §Inputs/§Outputs.

| Method | Path | Auth | Parameters | 200 response | Errors |
|---|---|---|---|---|---|
| GET | `/admin` | JWT (access token) + group `admin` | `page` (≥ 0, default 0), `size` (1..100, default 20), `sort` (`createdAt\|email\|familyName`,`asc\|desc`; default `createdAt,desc`) | `{ items: User[], page, size, total }` | 400, 401, 403, 500 |

`POST /chat` is unchanged (Week 5). No endpoint creates or updates data (requirements: no editing). Unknown query
parameters → 400.

## Affected Components

- **AWS (owner, runbooks):** Cognito group `admin` + membership (T03-01); `aws-challenge-admin` configuration, role
  and code upload (T03-07); API routes (delete `/api/...`), invoke permission check, CORS (T03-07).
- **Repository:** `lambdas/admin/` (handler + pytest, T03-06); `frontend/src` API client, role from the token,
  header, admin page (T03-08).
- **Skills:** `cognito-user-pool` (group, T03-01), `admin-api` (handler, T03-06), `http-api-jwt` (routes, T03-07),
  `spa-api-client` (endpoint, T03-08), `amplify-auth` (role from the session, T03-08).
- **Docs:** ENVIRONMENT.md (routes, CORS, admin settings), ARCHITECTURE §3.3, §6, ADR-018; CLAUDE.md §6; spec 05 note.

## Security Considerations

- Authentication at the edge (JWT authorizer, unchanged); the handler additionally rejects ID tokens
  (`token_use`), which pass the authorizer (ADR-004).
- Authorisation in the handler: only group `admin` reads other users' data; the SPA's role line and hidden link are
  cosmetic (they read an unverified local copy of the token payload — never used for access decisions).
- Claims are read only from `requestContext.authorizer.jwt.claims`, never from headers or query.
- Input: `page`, `size`, `sort` validated against the spec; sort column from a whitelist; parameterised SQL.
- The users list returns personal data to admins only; responses carry `Cache-Control: no-store`.
- Logs: no token, no e-mail or profile values (CLAUDE.md §7).
- No stage throttling until Week 6: abuse is bounded only by the account-level API Gateway limits and the authorizer
  (every call needs a valid token); accepted for the learning workload (owner, 2026-11-17).
- CORS lists only the Amplify origin and localhost (CORS is not access control).
- DB user shared across functions: R-16 (accepted for Week 3).

## Cost

No always-on resources. HTTP API about $1 per million requests; handler log ingestion and storage within the
learning volume ≈ $0 with 14-day retention. Database access per [user-sync](user-sync.md) §Cost.

## Open Questions

None open. Answered by the owner:

| ID | Question | Decision |
|---|---|---|
| [Q-18](../RISKS.md#q-18) | DB credentials / network path (shared with user-sync) | A — IAM auth to RDS Proxy (ADR-006 revised), 2026-11-13 |
| [Q-19](../RISKS.md#q-19) | Personal page source | A — Cognito profile, 2026-11-13; role line from the access token since 2026-11-17 (ADR-018) |
| ADR-018 | Route set | curriculum diagram: `GET /admin`, `POST /chat`; no `/api` prefix, no `/api/me`; access log and throttling in Week 6 — 2026-11-17 |
