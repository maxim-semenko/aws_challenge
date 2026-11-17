---
id: T03-06
title: "Admin Lambda: GET /api/me and GET /api/admin/users (Python, pytest)"
phase: P3-rest-api-data
status: Review
agent: backend
skills: [postgres-pro, test-master, http-api-jwt, admin-api]
depends_on: [T03-02]
blocked_by: []
design: ../../design/admin-api.md
spec: ../../specs/08-admin-api.md
acceptance: [AC-08.1]
---
# T03-06 — Admin Lambda: `GET /api/me` and `GET /api/admin/users`

## // BUSINESS CONTEXT

W3-G2, W3-G3, S3 (curriculum: "Admin Lambda ↔ RDS Proxy"): the administrator's users table needs a paginated,
admin-only endpoint over PostgreSQL; every user needs the own role. The `admin` code moves from the console into Git
(R-15).

## // TECHNICAL CONSTRAINTS

- Conventions of the `python-lambda` skill; shared DB helper; payload format 2.0; claims only from
  `requestContext.authorizer.jwt.claims`.
- Order of checks, responses, errors (problem+json), headers, log line: spec 08 character for character.
- `/api/me` makes no DB call (Q-19 A). Sort column from a fixed whitelist; parameterised SQL; `LIMIT/OFFSET`.
- No secret, token or user data in logs; DB failures → 500 with generic `detail`.
- The Week 1 direct-invoke probe is not kept (design admin-api §2).

## // SCOPE

**Implement**
- `lambdas/admin/` handler, `requirements.txt`, `tests/` covering AC-08.1; zip builds
- Update skill `python-lambda` (API handler section: routing, claims, problem+json, log line)

**Exclude**
- AWS changes (T03-07); SPA (T03-08); filtering by field (not in spec 08); `/api/admin/ping` (dropped)

**Interfaces that must match**
- Endpoint contract: spec 08 §Inputs/§Outputs; table columns: spec 06.

## Definition of Done

- [x] pytest green (AC-08.1); zip builds
- [ ] Skill updated (new skill `admin-api` written; pointer in `python-lambda` pending, see Notes); ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-18 (DB access) and Q-19 (`/api/me` content).
- 2026-11-13: Q-18 A and Q-19 A accepted by the owner (ADR-006 revised; `/api/me` from claims); design admin-api
  `Accepted` → `Todo` (waits for T03-02 `Done`); scope unchanged.
- 2026-11-16 (backend): start gate checked — T03-02 `Done`, design admin-api `Accepted`, not blocked. Implemented:
  `lambdas/admin/lambda_function.py` (routing on `routeKey`, claims from `requestContext.authorizer.jwt.claims`,
  401 → 404 → 403 → 400 → DB order, `cognito:groups` string/list parsing, query parsing from `rawQueryString`,
  six fixed page statements from the sort whitelist, problem+json, one JSON log line), `requirements.txt` (same pins
  as `sync`), `tests/conftest.py`, `tests/test_admin_api.py`, `tests/test_admin_api_integration.py` (optional, local
  PostgreSQL). Removed the placeholder `lambdas/admin/.gitkeep` (it was packaged into the zip). The Week 1 probe is
  not carried over.
- 2026-11-16 (backend): skill — new `.claude/skills/admin-api/SKILL.md` (routing, claims, problem+json, SQL, log
  line, tests) instead of a section in `python-lambda`, because `python-lambda` was being edited by the parallel
  T03-04 work. Pending (outside this task's write set): a one-line pointer to `admin-api` in `python-lambda`
  (§Layout / §Log line), a row for `admin` in `lambdas/README.md`, and `admin-api` in the `backend` agent's
  `skills:` front matter if the owner wants it loaded by default.
- 2026-11-16 (backend): verification, local Python 3.13.x, private venv with `lambdas/requirements-dev.txt` + the
  runtime pins (identical in `sync` and `admin`):
  - `python -m pytest lambdas/shared lambdas/admin` → **108 passed, 6 skipped** (the 6 = integration test, skipped:
    `MIGRATE_TEST_DATABASE_URL` not set, Docker Desktop not running) — integration against PostgreSQL **not verified**.
  - AC-08.1 coverage: ID token → 401 (both routes, no DB call); missing claims / `sub` / `exp` → 401; unknown route →
    404; no or other group → 403 without DB call; every invalid parameter of spec 08 Edge Cases (`size=0`,
    `size=101`, `page=-1`, `page=abc`, `sort=email`, `sort=password,asc`, `foo=1`, `page=1&page=2`) and more → 400
    naming the parameter, no DB call; `/api/me` with any parameter → 400; group formats `[admin]`, `admin`,
    `[admin user]`, JSON array, list; empty table; page beyond the end; connect failure and query failure → 500
    generic detail, `errorClass`, connection closed; `/api/me` mapping (`expiresAt` ISO-8601 UTC); users mapping
    (camelCase, `YYYY-MM-DD`, UTC timestamps, nulls, odd values); exact SQL per sort combination, hostile `sort`
    never reaches SQL; log line keys, no token / e-mail / names in it.
  - 3.12 compatibility: static check only (no 3.13-only API used; `py` has no 3.12).
  - `py -3.13 lambdas/package.py admin` → `build/lambdas/admin.zip`: **90 files, 432258 bytes**, SHA-256
    `497f819a0df3af964b155ba970892b8acb97bd33f59b47392d0851fc4c45b4da`, base64
    `SX+Bmg3zr5ZLFVupcIkrisuXvTP1m0c5LQhR/ExFtNo=` (built with `lambdas/shared/db.py` SHA-256
    `e3e71eb0…ff349c`). The zip includes `db.py`; if T03-04 changes `db.py`, rebuild before the T03-07 upload and use
    the new hash.
  - AC-08.2 … AC-08.9: AWS-side, not verifiable here (T03-01, T03-07, T03-10).
- ARCH review 2026-11-16: **pass** (no blocking findings). Checked against design admin-api §2, spec 08, the SPA
  contract in `frontend/src/api/client.ts` (spec 09) and the TECHNICAL CONSTRAINTS:
  - Order 401 (claims, `sub`, `exp`, `token_use == "access"`) → 404 (`routeKey`) → 403 (before parameters, no DB
    call) → 400 → DB; claims only from `requestContext.authorizer.jwt.claims`; `/api/me` without DB call.
  - `cognito:groups`: `[admin]`, `admin`, `[admin user]`, JSON array, list parsed; exact-case match. Sort: request
    input only selects one of six import-time constant statements; `LIMIT/OFFSET` as pg8000 parameters — no
    injection path. Pagination `{items, page, size, total}` and `User` fields match `client.ts` (`Page<User>`,
    `MeResponse`); SPA sends only `page` and `size=20`. problem+json body/headers, `Cache-Control: no-store`, generic
    500 detail, log line keys per spec 08 without token, header, e-mail, names or rows.
  - Re-run in a fresh venv (Python 3.13.x): `pytest lambdas/shared lambdas/admin` → 108 passed, 6 skipped
    (integration against PostgreSQL **not verified**). `py -3.13 lambdas/package.py admin` → 90 files, SHA-256
    `497F819A…C45B4DA` — identical to the hash above (reproducible; `db.py` still `e3e71eb0…ff349c`). Python 3.12:
    `ast.parse(feature_version=(3,12))` ok and no 3.13-only API found; not run on a 3.12 interpreter (**not verified**).
  - Notes item "pending" above is resolved: `python-lambda` points to `admin-api` (Layout section) and
    `lambdas/README.md` has the `admin` row.
  - Non-blocking: (1) `parse_groups` also splits on commas; Cognito group names may contain `,`, so a group named
    e.g. `x,admin` would count as `admin` — groups are owner-managed only, low risk; option: split on whitespace only
    (API Gateway uses spaces) or record the rule in the cognito-user-pool skill. (2) The task SCOPE / design
    Affected Components name a `python-lambda` "API handler section"; realised as the separate skill `admin-api` —
    the owner may want `admin-api` added to this task's `skills:` (and PLAN.md row) and to the `backend` agent.
    (3) `/api/me?&` counts as "no parameter" (empty pairs are dropped by `parse_qsl`) — harmless.
- 2026-11-17 owner decision: the HTTP API follows the curriculum architecture diagram strictly — only `GET /admin`
  (admin panel queries → `aws-challenge-admin`) and `POST /chat` (Week 5, chatbot); no `/api` prefix, no `/api/me`,
  no `/api/admin/users`. The title, SCOPE and the `/api/me` constraint above describe the superseded routes.
- 2026-11-17 (backend): `lambdas/admin/lambda_function.py` — users list moved to routeKey `GET /admin` (`ROUTE_USERS`),
  behaviour unchanged (401 → 404 → 403 → 400 → DB, `rawQueryString` parsing, `{items,page,size,total}`,
  problem+json, one log line); `GET /api/me` handler and its no-parameter check removed; every other routeKey (also
  `GET /api/me`, `GET /api/admin/users`, `POST /chat`) → 404. Tests updated (`/api/me` tests removed, 404 cases for
  the old routes added, integration event on `GET /admin`); skill `admin-api` and `lambdas/README.md` row updated.
  Verification (fresh venv outside the repo, Python 3.13.2):
  - `pytest lambdas/shared lambdas/admin` → **104 passed, 6 skipped** (integration test skipped,
    `MIGRATE_TEST_DATABASE_URL` not set — against PostgreSQL **not verified**).
  - 3.12: `ast.parse(feature_version=(3,12))` ok, no 3.13-only API — static check only.
  - `py -3.13 lambdas/package.py admin` → `build/lambdas/admin.zip`: **90 files, 432098 bytes**, SHA-256
    `d82bbf9aad1fac45e5d608dafed71f73395227f1fd165b635bed1ac0e5c7d47a`, base64
    `2Cu/mq0frEXl1gja/tcfczlSJ/H9FltjW+0awOXH1Ho=` (`db.py` unchanged, `e3e71eb0…ff349c`). Supersedes the 2026-11-16
    hash `497f819a…`; the T03-07 upload must use this zip.
  - Not changed here (other agents): spec 08, design admin-api, PLAN.md, frontend, the T03-07 route runbook.
