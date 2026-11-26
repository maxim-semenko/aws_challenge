---
name: admin-api
description: How the API handler aws-challenge-admin (lambdas/admin) serves the route GET /admin behind the HTTP API JWT authorizer — payload 2.0 routing on routeKey, claims only from requestContext.authorizer.jwt.claims, token_use and admin group checks, cognito:groups string formats, query parsing from rawQueryString, problem+json errors, the sort whitelist with fixed SQL, the response mapping formats, the one-JSON-line log and the pytest doubles. Use when changing lambdas/admin or reviewing evidence for spec 08.
license: MIT
metadata:
  domain: backend
  triggers: lambdas/admin, aws-challenge-admin, GET /admin, routeKey, payload 2.0, jwt claims, token_use, cognito:groups, problem+json, rawQueryString, sort whitelist, apiRequestId
  role: specialist
  scope: implementation
  related-skills: python-lambda, http-api-jwt, spa-api-client, postgres-pro, test-master, chatbot-api
  source: project (created by T03-06; shared HTTP helpers moved to lambdas/shared by T05-02)
  used-by: [backend, tester, devops]
---

# Admin API handler (`lambdas/admin`)

Contract (single home): [spec 08](../../../docs/specs/08-admin-api.md) §Inputs/§Outputs; design
[admin-api](../../../docs/design/admin-api.md) §2; conventions CLAUDE.md §6. Layout, packaging, DB helper and log
rules in general: [python-lambda](../python-lambda/SKILL.md). API, authorizer, routes, CORS:
[http-api-jwt](../http-api-jwt/SKILL.md). This file says how the handler implements the contract — never copy the
field tables here.

Shared helpers (T05-02): claims (`claims`, `expiry`, `authorized`), `parse_groups`, `is_admin`, `ApiError`, `problem`,
`json_response`, the 401/403/404/500 texts and `TITLES` live in **`lambdas/shared/http_api.py`** (tests:
`lambdas/shared/tests/test_http_api.py`) and are used by `admin` and `chatbot` (chatbot-api skill); the handler
imports them (`parse_groups` stays importable from `lambda_function` for the admin tests). A change there changes both
APIs — run `pytest lambdas/shared lambdas/admin` and `… lambdas/chatbot`.

Routes (owner decision 2026-11-17, curriculum architecture diagram): the HTTP API has exactly two routes, `GET /admin`
(this function, the users list) and `POST /chat` (Week 5, `aws-challenge-chatbot`) — no `/api` prefix, no `/api/me`
(the SPA reads the role from the token).

## Request flow (`lambda_function.lambda_handler`)

1. Claims only from `event.requestContext.authorizer.jwt.claims` (never headers, query or body). 401 unless `sub` is a
   non-empty string, `token_use == "access"` (ID tokens pass the authorizer, ADR-004) and `exp` is epoch seconds
   (payload v2 delivers every claim as a **string**).
2. Route on `event.routeKey` (`ROUTE_USERS = "GET /admin"`); anything else (including the removed `GET /api/me`,
   `GET /api/admin/users`) → 404. Unknown paths and methods never reach the function in practice (no route in API
   Gateway); the 404 is defensive.
3. `"admin"` in the parsed groups, else 403 — before parameter validation and before any DB call.
4. Query parameters → 400 (`detail` names the parameter, truncated to 64 chars; never echoes the value).
5. Database: `db.connect()` lazily, two statements, `db.close_quietly` in `finally`.

`cognito:groups` (`http_api.parse_groups`): `"[admin]"`, `"admin"`, `"[admin user]"` (space-separated inside brackets), a JSON
array string or a real list; commas are separators too; absent → `[]`. Exact-case match on `admin`. Re-check the real
format in the first deployed log/test (spec 08 Edge Cases) — the parser accepts all forms seen so far.

Query parsing uses **`rawQueryString`** (`urllib.parse.parse_qsl`, blanks kept): `queryStringParameters` joins
repeated values with commas, which cannot be told apart from the comma inside `sort=createdAt,desc`. The dict is only
a fallback for hand-made events without `rawQueryString`. Integers: ASCII digits only (`[0-9]+`, leading zeros ok),
so `+5`, `1.5`, `-1`, non-ASCII digits are 400. `sort` is case-sensitive.

## SQL

- `SQL_COUNT` and one fixed `SQL_PAGE[(field, direction)]` per whitelisted combination, built at import time from
  the constant maps `SORT_COLUMNS` / `SORT_DIRECTIONS` — request input only selects a key, never reaches the text.
- `ORDER BY <column> <ASC|DESC> NULLS LAST, id LIMIT :limit OFFSET :offset`; `offset = page * size` (max 10^8, fits).
- Explicit column list (`USER_COLUMNS`), no `SELECT *`; adding a column = migration (postgres-migrations skill) +
  `USER_COLUMNS` + `map_user` + spec 08 change.
- Count and page are two autocommit statements (no transaction): a concurrent insert can make `total` differ by one
  from the page content; accepted for a read-only admin table.

## Responses

- Payload v2 dict with `statusCode`, `headers` (`Content-Type`, `Cache-Control: no-store`), `body` (compact JSON,
  `ensure_ascii=False`), `isBase64Encoded: false`. CORS headers come from API Gateway, not the handler.
- 200 `application/json`; errors `application/problem+json` `{type: "about:blank", title, status, detail}` with
  fixed `detail` texts for 401/403/404/500 (500 never contains SQL, SQLSTATE, host or exception text).
- Formats in `map_user`: UUID → string; `date` → `YYYY-MM-DD`; timestamps → UTC `YYYY-MM-DDTHH:MM:SSZ` (seconds; a naive
  value is taken as UTC); text and integers as stored, `NULL` → `null`.

## Log line

One line from `finally` per request: `level` (`INFO` 2xx, `WARNING` 4xx, `ERROR` 5xx), `message` (`request
completed`; on 5xx `DB_CONNECT_FAILED` or `INTERNAL_ERROR`), `function`, `awsRequestId`, `apiRequestId`
(`requestContext.requestId` = `requestId` of the API access log), `userSub` (claim `sub`, `null` without claims),
`route` (routeKey), `status`, `durationMs`, `outcome` (`success` / `client_error` / `failure`), `errorClass` on 5xx
only (class name; for `DbConnectError` the class of its `__cause__`). Never the token, headers, query values,
e-mail, names or rows.

## Tests

```powershell
.venv\Scripts\python -m pytest lambdas/shared lambdas/admin
```

- `tests/test_admin_api.py`: events built like payload v2 (`routeKey`, `rawQueryString`, `requestContext.requestId`,
  `authorizer.jwt.claims` with string values); `db.connect` monkeypatched to a `FakeConnection` that only accepts
  `SQL_COUNT` / `SQL_PAGE` statements and slices its rows by `limit`/`offset` (ordering is the database's job);
  `capsys` reads the single log line. A failing connect is `db.DbConnectError` with a `__cause__`.
- `tests/test_admin_api_integration.py`: optional, real PostgreSQL 14 (`docker compose up -d`,
  `MIGRATE_TEST_DATABASE_URL` as for sync); builds `users` from `lambdas/sync/migrations` in a throw-away schema and
  checks sort order, `NULLS LAST`, id tiebreak, paging and type mapping.

## Adding a route to this function

Only with an owner decision (the API follows the curriculum diagram: `GET /admin`, `POST /chat`). Spec first
(fields, errors, ACs), then: a branch in `_route` (group check before parameters), a parser that rejects unknown/repeated parameters, fixed SQL only, tests for every error row; the route itself is added
to API Gateway by the devops runbook (http-api-jwt skill: explicit method, JWT authorizer, payload 2.0), and the SPA
side by the frontend task (spa-api-client skill).
