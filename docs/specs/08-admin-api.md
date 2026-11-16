# Spec 08 — Admin API: `GET /api/me`, `GET /api/admin/users`, group `admin`, logs

Requirements: [week-03](../requirements/week-03-rest-api-data.md) W3-G2, W3-G3, W3-G5, S3, S4, S7, S8 ·
Design: [admin-api](../design/admin-api.md) §1–§3
Tasks: T03-01, T03-06, T03-07, T03-10

Written against [Q-18](../RISKS.md#q-18) option A and [Q-19](../RISKS.md#q-19) option A — both accepted by the
owner on 2026-11-13; re-checked, no change needed. Replaces the Week 2 routes of [spec 05](05-protected-api.md) (AC-05.2
route list) — the authorizer behaviour of spec 05 still applies to the new routes.

## Purpose

The HTTP API `aws-challenge-api` serves two endpoints from the Admin Lambda under `/api`, following CLAUDE.md §6:
every signed-in user reads the own identity and groups; only members of the Cognito group `admin` read the paginated
list of users from PostgreSQL through RDS Proxy. API Gateway writes a JSON access log and the handler one JSON line
per request, correlated by `apiRequestId`.

## Inputs

**Common:** header `Authorization: Bearer <access token>` of the pool/app client (ADR-004), validated by the JWT
authorizer (spec 05). The handler reads claims only from `requestContext.authorizer.jwt.claims`: `sub`,
`token_use`, `username`, `cognito:groups` (optional), `exp`.

**`GET /api/me`** — no query parameters, no body. Any query parameter → 400.

**`GET /api/admin/users`** — query parameters (only these; any other → 400; each at most once):

| Name | Type | Valid range | Default | Required |
|---|---|---|---|---|
| `page` | integer (decimal digits) | 0 … 1 000 000 | `0` | no |
| `size` | integer (decimal digits) | 1 … 100 | `20` | no |
| `sort` | string `<field>,<direction>` | field `createdAt` \| `email` \| `familyName`; direction `asc` \| `desc` | `createdAt,desc` | no |

No request body on either endpoint; no endpoint creates or updates data.

**Lambda configuration:** DB variables of spec 06 §Inputs.

## Outputs

All JSON bodies UTF-8, field names camelCase, header `Cache-Control: no-store`.

**`GET /api/me` → 200** `application/json`:

| Field | Type | Value |
|---|---|---|
| `id` | string | claim `sub` |
| `username` | string \| null | claim `username` |
| `groups` | string[] | parsed `cognito:groups`; `[]` when absent |
| `expiresAt` | string | claim `exp` as ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`) |

**`GET /api/admin/users` → 200** `application/json`: `{ "items": User[], "page": n, "size": n, "total": n }` where
`page`/`size` are the effective values and `total` is the number of rows in `users`. `User`:

| Field | Type | From column (spec 06) |
|---|---|---|
| `id` | string (UUID) | `id` |
| `email` | string | `email` |
| `givenName`, `familyName`, `gender`, `country` | string \| null | `given_name`, `family_name`, `gender`, `country` |
| `birthdate` | string `YYYY-MM-DD` \| null | `birthdate` |
| `heightCm`, `weightKg` | integer \| null | `height_cm`, `weight_kg` |
| `createdAt`, `updatedAt` | string ISO-8601 UTC | `created_at`, `updated_at` |

Order: the `sort` column and direction, then `id` ascending (stable); `NULL` values last. A page beyond the end →
`items: []` with the correct `total`.

**Errors** (handler) — `application/problem+json`, body `{ "type": "about:blank", "title", "status", "detail" }`:

| Status | When | `title` |
|---|---|---|
| 400 | unknown, repeated or invalid query parameter (`detail` names the parameter) | `Bad Request` |
| 401 | claims missing or `token_use` ≠ `access` | `Unauthorized` |
| 403 | `/api/admin/*` and `admin` not in groups | `Forbidden` |
| 404 | route key not served by the handler | `Not Found` |
| 500 | database or unexpected error (`detail` generic, no SQL/host) | `Internal Server Error` |

Fixed API Gateway bodies (exception, ARCHITECTURE §3.3): authorizer 401 `{"message":"Unauthorized"}`; unknown route
404 `{"message":"Not Found"}`; throttled 429 `{"message":"Too Many Requests"}`.

**Handler log line** (one JSON object per request): `level`, `message`, `function`, `awsRequestId`, `apiRequestId`
(`requestContext.requestId`), `userSub`, `route` (route key), `status`, `durationMs`, `outcome` (`success` /
`client_error` / `failure`), `errorClass` (on 5xx). Never: the token, the `Authorization` header, e-mail or other
user data, query results.

**API access log** (stage `$default`, log group `/aws/apigateway/aws-challenge-api`, retention 14 days), one JSON
object per request with exactly these keys:

```json
{"requestId":"$context.requestId","requestTime":"$context.requestTime","routeKey":"$context.routeKey","status":"$context.status","responseLatency":"$context.responseLatency","integrationLatency":"$context.integrationLatency","integrationError":"$context.integrationErrorMessage","authorizerError":"$context.authorizer.error","userSub":"$context.authorizer.claims.sub"}
```

No source IP, user agent or headers.

## Behaviour

1. API Gateway answers CORS preflights (origins: the Amplify origin and `http://localhost:5173`, max age 600 s),
   applies stage throttling (50 rps, burst 100) and the JWT authorizer (spec 05) to `GET /api/me` and
   `GET /api/admin/users`; on success it invokes `aws-challenge-admin` (payload 2.0).
2. The handler starts the timer, reads the claims; missing claims or `token_use` ≠ `access` → 401.
3. It dispatches on `routeKey`; unknown → 404.
4. `GET /api/me`: rejects any query parameter (400), returns the claims mapping. No database call.
5. `GET /api/admin/users`: `admin` ∉ groups → 403 (no database call); validates parameters → 400; opens one proxy
   connection (spec 06), runs `SELECT count(*) FROM users` and the page query (`ORDER BY <whitelisted column>
   <direction> NULLS LAST, id LIMIT size OFFSET page*size`), closes the connection, returns 200.
6. Every path writes one log line and returns a payload-v2 response with explicit `statusCode`, headers and body.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| ID token of the same app client | passes the authorizer, handler → 401 problem+json |
| Access token of a user in no group | `/api/me` → 200 with `groups: []`; `/api/admin/users` → 403 |
| `cognito:groups` claim delivered as `"[admin]"`, `"admin"` or `"[admin user]"` | parsed to `["admin"]` / `["admin","user"]` |
| User added to `admin` but still on an old token | 403 until the token is refreshed or the user signs in again |
| `size=0`, `size=101`, `page=-1`, `page=abc`, `sort=email`, `sort=password,asc`, `foo=1`, `page=1&page=2` | 400, `detail` names the parameter |
| `page` beyond the last page | 200, `items: []`, `total` correct |
| Empty table | 200, `items: []`, `total: 0` |
| Row with NULL or odd values (spec 07) | returned as `null` / as stored |
| Proxy unreachable, IAM auth failure | 500 problem+json, log `outcome=failure`, `errorClass` set |
| Old route `GET /admin` | 404 from API Gateway (route deleted) |
| Method not served (e.g. `POST /api/me`) | 404 from API Gateway (no route); preflight still 204 |

## Acceptance Criteria

AWS-side criteria are verified from evidence the owner provides (console screenshots, status codes from the deployed
SPA's browser console or `curl` without a token, log events); agents have no AWS access (CLAUDE.md §3.11). Token
values never appear in the evidence. AC-08.1 is verified locally.

- [ ] AC-08.1 `pytest` for `lambdas/admin` passes and covers every row of §Outputs errors and §Edge Cases that
  concerns the handler (ID token → 401; no group → 403 without DB call; each invalid parameter → 400; group claim
  formats; empty table; page beyond the end; DB error → 500), the `/api/me` mapping, the users mapping (camelCase,
  `YYYY-MM-DD`, ISO-8601 UTC, nulls), the sort whitelist (no input in the SQL string) and the log line fields
- [ ] AC-08.2 Group `admin` exists in `aws-challenge-users` and the owner's account is a member (owner screenshot)
- [ ] AC-08.3 The API's routes are exactly `GET /api/me` and `GET /api/admin/users`, both with the JWT authorizer and
  the Lambda integration `aws-challenge-admin` (payload 2.0); `GET /admin` and `POST /chat` are gone; no `ANY`,
  `OPTIONS` or `$default` route (owner screenshot)
- [ ] AC-08.4 Without a token `GET /api/me` and `GET /api/admin/users` → 401; preflight `OPTIONS /api/admin/users`
  from the Amplify origin → 204 with `Access-Control-Allow-Origin` = that origin
- [ ] AC-08.5 Signed in as a non-admin on the deployed SPA: `GET /api/me` → 200 with `groups: []`;
  `GET /api/admin/users` → 403 `application/problem+json`
- [ ] AC-08.6 Signed in as the admin: `GET /api/me` → 200 with `groups` containing `admin`;
  `GET /api/admin/users?page=0&size=2` → 200 with `size: 2`, at most 2 items and `total` = number of rows;
  `?size=101` → 400 problem+json
- [ ] AC-08.7 The access log group has retention 14 days and contains a JSON line for an AC-08.6 request whose
  `requestId` equals the `apiRequestId` of the handler log line of the same request; neither line contains a token,
  e-mail or profile value (owner screenshots of both log events)
- [ ] AC-08.8 Stage `$default` shows default route throttling rate 50 / burst 100; CORS origins are the Amplify origin
  and `http://localhost:5173`, max age 600; the Lambda resource policy allows `apigateway.amazonaws.com` only with a
  `SourceArn` of this API (owner screenshots, account id masked)
- [ ] AC-08.9 `aws-challenge-admin` runs Python 3.12 (ADR-015 revised 2026-11-16) with the code zip built from Git (`lambdas/admin`), timeout 10 s,
  memory 256 MB, env vars per spec 06, role with `rds-db:connect` only for DB access (AC-06.6 covers secrets)
