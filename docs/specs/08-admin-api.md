# Spec 08 — Admin API: `GET /admin` (users list), group `admin`, handler log

Requirements: [week-03](../requirements/week-03-rest-api-data.md) W3-G2, W3-G3, W3-G5, S3, S4, S7, S8 ·
Design: [admin-api](../design/admin-api.md) §1–§3 · ADR-018
Tasks: T03-01, T03-06, T03-07, T03-10

Written against [Q-18](../RISKS.md#q-18) option A and [Q-19](../RISKS.md#q-19) option A (owner, 2026-11-13) and
ADR-018 (owner, 2026-11-17: routes exactly as in the curriculum diagram, no `/api` prefix, no `/api/me`; API access
log and stage throttling deferred to Week 6). The routes stay those of [spec 05](05-protected-api.md) AC-05.2
(`GET /admin`, `POST /chat`); the authorizer behaviour of spec 05 still applies.

## Purpose

The HTTP API `aws-challenge-api` serves `GET /admin` from the Admin Lambda, following CLAUDE.md §6: only members of
the Cognito group `admin` read the paginated list of users from PostgreSQL through RDS Proxy; everybody else gets
403. The handler writes one JSON log line per request, correlated by `apiRequestId`. `POST /chat` is unchanged
(Week 5).

## Inputs

**Common:** header `Authorization: Bearer <access token>` of the pool/app client (ADR-004), validated by the JWT
authorizer (spec 05). The handler reads claims only from `requestContext.authorizer.jwt.claims`: `sub`,
`token_use`, `cognito:groups` (optional).

**`GET /admin`** — query parameters (only these; any other → 400; each at most once):

| Name | Type | Valid range | Default | Required |
|---|---|---|---|---|
| `page` | integer (decimal digits) | 0 … 1 000 000 | `0` | no |
| `size` | integer (decimal digits) | 1 … 100 | `20` | no |
| `sort` | string `<field>,<direction>` | field `createdAt` \| `email` \| `familyName`; direction `asc` \| `desc` | `createdAt,desc` | no |

No request body; no endpoint creates or updates data.

**Lambda configuration:** DB variables of spec 06 §Inputs.

## Outputs

All JSON bodies UTF-8, field names camelCase, header `Cache-Control: no-store`.

**`GET /admin` → 200** `application/json`: `{ "items": User[], "page": n, "size": n, "total": n }` where
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
| 403 | `admin` not in groups | `Forbidden` |
| 404 | route key other than `GET /admin` | `Not Found` |
| 500 | database or unexpected error (`detail` generic, no SQL/host) | `Internal Server Error` |

Fixed API Gateway bodies (exception, ARCHITECTURE §3.3): authorizer 401 `{"message":"Unauthorized"}`; unknown route
404 `{"message":"Not Found"}`.

**Handler log line** (one JSON object per request, log group `/aws/lambda/aws-challenge-admin`, retention 14 days):
`level`, `message`, `function`, `awsRequestId`, `apiRequestId` (`requestContext.requestId`), `userSub`, `route`
(route key), `status`, `durationMs`, `outcome` (`success` / `client_error` / `failure`), `errorClass` (on 5xx).
Never: the token, the `Authorization` header, e-mail or other user data, query results.

API access log and stage throttling: deferred to Week 6 (ADR-018); not part of this spec.

## Behaviour

1. API Gateway answers CORS preflights (origins: the Amplify origin and `http://localhost:5173`, max age 600 s) and
   applies the JWT authorizer (spec 05) to `GET /admin`; on success it invokes `aws-challenge-admin` (payload 2.0).
2. The handler starts the timer, reads the claims; missing claims or `token_use` ≠ `access` → 401.
3. It dispatches on `routeKey`; anything but `GET /admin` → 404.
4. `GET /admin`: `admin` ∉ groups → 403 (no database call); validates parameters → 400; opens one proxy connection
   (spec 06), runs `SELECT count(*) FROM users` and the page query (`ORDER BY <whitelisted column> <direction> NULLS
   LAST, id LIMIT size OFFSET page*size`), closes the connection, returns 200.
5. Every path writes one log line and returns a payload-v2 response with explicit `statusCode`, headers and body.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| ID token of the same app client | passes the authorizer, handler → 401 problem+json |
| Access token of a user in no group | 403 problem+json, no database call |
| `cognito:groups` claim delivered as `"[admin]"`, `"admin"` or `"[admin user]"` | parsed to `["admin"]` / `["admin","user"]` |
| User added to `admin` but still on an old token | 403 until the token is refreshed or the user signs in again |
| `size=0`, `size=101`, `page=-1`, `page=abc`, `sort=email`, `sort=password,asc`, `foo=1`, `page=1&page=2` | 400, `detail` names the parameter |
| `page` beyond the last page | 200, `items: []`, `total` correct |
| Empty table | 200, `items: []`, `total: 0` |
| Row with NULL or odd values (spec 07) | returned as `null` / as stored |
| Proxy unreachable, IAM auth failure | 500 problem+json, log `outcome=failure`, `errorClass` set |
| Former paths `/api/me`, `/api/admin/users` | 404 from API Gateway (routes deleted 2026-11-17) |
| Method not served (e.g. `POST /admin`) | 404 from API Gateway (no route); preflight still 204 |

## Acceptance Criteria

AWS-side criteria are verified from evidence the owner provides (console screenshots, status codes from the deployed
SPA's browser console or `curl` without a token, log events); agents have no AWS access (CLAUDE.md §3.11). Token
values never appear in the evidence. AC-08.1 is verified locally.

- [ ] AC-08.1 `pytest` for `lambdas/admin` passes and covers every row of §Outputs errors and §Edge Cases that
  concerns the handler (ID token → 401; no group → 403 without DB call; each invalid parameter → 400; group claim
  formats; empty table; page beyond the end; DB error → 500; other route key → 404), the users mapping (camelCase,
  `YYYY-MM-DD`, ISO-8601 UTC, nulls), the sort whitelist (no input in the SQL string) and the log line fields
- [ ] AC-08.2 Group `admin` exists in `aws-challenge-users` and the owner's account is a member (owner screenshot)
- [ ] AC-08.3 The API's routes are exactly `GET /admin` (JWT authorizer, Lambda integration `aws-challenge-admin`,
  payload 2.0) and `POST /chat` (JWT authorizer, chatbot integration); no `/api/...`, `ANY`, `OPTIONS` or `$default`
  route (owner screenshot)
- [ ] AC-08.4 Without a token `GET /admin` and `POST /chat` → 401 and `/api/me` → 404; preflight `OPTIONS /admin` from
  the Amplify origin → 204 with `Access-Control-Allow-Origin` = that origin
- [ ] AC-08.5 Signed in as a non-admin on the deployed SPA: `GET /admin` → 403 `application/problem+json`
- [ ] AC-08.6 Signed in as the admin: `GET /admin?page=0&size=2` → 200 with `size: 2`, at most 2 items and `total` =
  number of rows; `GET /admin?size=101` → 400 problem+json
- [ ] AC-08.7 The handler log group has retention 14 days and contains one JSON line for an AC-08.6 request with
  `route` `GET /admin`, `status` 200, `apiRequestId` and `userSub` set; no line contains a token, e-mail or profile
  value (owner screenshot of the log event). The API access log is Week 6 (ADR-018)
- [ ] AC-08.8 CORS origins are the Amplify origin and `http://localhost:5173`, max age 600; the Lambda resource policy
  of `aws-challenge-admin` allows `apigateway.amazonaws.com` only with a `SourceArn` of this API (owner screenshots,
  account id masked). Stage throttling is Week 6 (ADR-018)
- [ ] AC-08.9 `aws-challenge-admin` runs Python 3.12 (ADR-015 revised 2026-11-16) with the code zip built from Git (`lambdas/admin`), timeout 10 s,
  memory 256 MB, env vars per spec 06, role with `rds-db:connect` only for DB access (AC-06.6 covers secrets)
