---
id: T03-10
title: "Week 3 acceptance check"
phase: P3-rest-api-data
status: Done
agent: tester
skills: [test-master]
depends_on: [T03-01, T03-02, T03-03, T03-04, T03-05, T03-06, T03-07, T03-08, T03-09]
blocked_by: []
design: null  # acceptance task, verifies specs 06-09 and the spec 01/04/05 regressions
spec: [../../specs/01-spa-delivery.md, ../../specs/06-users-table-and-migrations.md, ../../specs/07-user-sync.md, ../../specs/08-admin-api.md, ../../specs/09-admin-page-and-role.md]
acceptance: [AC-06.1, AC-06.2, AC-06.3, AC-06.4, AC-06.5, AC-06.6, AC-07.1, AC-07.2, AC-07.3, AC-07.4, AC-07.5, AC-07.6, AC-08.1, AC-08.2, AC-08.3, AC-08.4, AC-08.5, AC-08.6, AC-08.7, AC-08.8, AC-08.9, AC-09.1, AC-09.2, AC-09.3, AC-09.4, AC-09.5, AC-01.2]
---
# T03-10 — Week 3 acceptance check

## // BUSINESS CONTEXT

Week 3 ("REST API + data") is done only when the chain sign-up → owner confirms → row in PostgreSQL → admin table,
the 401/403 rules and the logs are proven on `dev` by someone other than the implementer. The report is what the
owner shows to the mentor.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11). Local ACs (pytest of each function, zip builds, `npm test`,
  `npm run build`, repository contents, `git grep` for secrets) run by the tester; AWS-side ACs from owner evidence;
  public unauthenticated probes (`curl` without a token) allowed.
- Evidence already in T03-01 … T03-09 Notes is reused by pointer; only missing evidence is requested.
- Each AC: pass / fail / not verifiable + source + trimmed output; account ids masked; no tokens; no personal data of
  test users beyond the e-mail domain.
- Regression: spec 04 AC-04.10, spec 05 AC-05.3 (on the new routes), spec 01 AC-01.1/AC-01.2.

## // SCOPE

**Implement**
- Owner checklist for missing evidence; report table AC → result → evidence in Notes

**Exclude**
- Fixing defects (reported to the owning task), E2E suite

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All listed ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning.
- 2026-11-17 (architect): ADR-018 — spec 08 now covers only `GET /admin` (no `/api/...` routes); AC ids unchanged,
  AC-08.7 is the handler log only and AC-08.8 CORS + resource policy only (API access log and throttling: Week 6).
  Regression AC-05.2 (routes `GET /admin`, `POST /chat`) holds again.
- 2026-11-17 (tester): acceptance run → status `In progress` (8 ACs lack owner evidence; no failure). Report below.

## Acceptance report (tester, 2026-11-17)

**Own runs** (no AWS credentials; Git `66be514` + uncommitted docs only, `lambdas/` and `frontend/` unchanged):

- Lambdas — Python 3.13.2 venv in `%TEMP%` from `lambdas/requirements-dev.txt` + `sync`/`admin` pins (removed
  afterwards); one pytest session per function (python-lambda skill: every function has a module `lambda_function`,
  so one combined session fails on the name clash by design — 86 collisions, not a defect):
  `lambdas/shared lambdas/sync` **134 passed, 2 skipped** · `lambdas/post-confirmation` **13 passed** ·
  `lambdas/shared lambdas/admin` **104 passed, 6 skipped** (admin alone 91 + 6) · `lambdas/tests` **7 passed**.
  The 8 skips are the optional PostgreSQL 14 integration tests (`MIGRATE_TEST_DATABASE_URL` unset; Docker engine not
  running) — upsert / page SQL against a real PostgreSQL 14 **not verified locally** (proven on AWS by AC-06.5,
  AC-07.4, AC-09.3).
- Packager reproducibility — `py -3.13 lambdas/package.py <fn>`, built twice from the working copy, identical, and
  equal to the deployed console hashes: `sync` 93 files `B02EB57C…0BC5F20B` / `sC61fMxGFz0KgcGNiu69NWti6KB6LZCgCUkhSQvF8gs=`;
  `post-confirmation` 2 files `0BDCBA9F…434F60F4` / `C9y6n5f2GwycYasAoryO/qrbt5c0Og1UUOU3O0NPYPQ=`; `admin` 90 files
  `D82BBF9A…E5C7D47A` / `2Cu/mq0frEXl1gja/tcfczlSJ/H9FltjW+0awOXH1Ho=`. From a clean `git archive HEAD` export: `sync`
  and `post-confirmation` identical; `admin` differs (`182BCC71…B8AAC560`) — only `lambda_function.py` differs and it is
  byte-equal after CRLF→LF (known T03-06 caveat confirmed: `git ls-files --eol` `i/lf w/crlf`).
- Frontend — `npm ci`, `npm test` **7 files / 70 tests passed**, `npm run build` (`tsc -b` + vite) green. AC-09.2:
  no `.env*` besides `.env.example`, no `VITE_*` in the shell, bundle without `execute-api`; `vite preview` rendered in
  headless Chrome with a net log: `/` intro only; `/admin` "Users" + "Not available yet — coming in a later week.";
  app requests only `/`, `/admin`, the two assets, `favicon.svg` (other entries are Chrome's own Google services).
- Repository — `V1__create_users.sql` read against spec 06 §Outputs (12 columns, types, NULL/NOT NULL, defaults, PK
  only); `git grep` in `lambdas/` for password/secret/`DB_SECRET_ARN`/credential URLs/AWS keys: only the IAM-token
  `password=token` in `shared/db.py` and the local Docker URL `app:app@localhost` in three integration-test
  docstrings (local compose credentials, not a secret). `AdminPage.tsx` has only Retry/Previous/Next buttons.
- Public probes (curl, 2026-11-17): Amplify `/`, `/admin`, `/chat`, `/sign-in` → 200 `text/html`, no `Location`,
  `Via …cloudfront.net`, `X-Amz-Cf-Id` present, `X-Cache: Hit from cloudfront`; `/x.js` → 404. API
  `o6cpz238i3`: `GET /admin` no token → 401 `{"message":"Unauthorized"}`; `Bearer abc` → 401; `POST /chat` → 401;
  `/api/me` → 404 `{"message":"Not Found"}`; `/api/admin/users` → 404; `POST /admin` → 404; `/unknown`, `/` → 404
  (no `$default`/`ANY` route); preflight `OPTIONS /admin` from the Amplify origin → 204, allow-origin = that origin,
  `max-age 600`, headers `authorization,content-type`; from `http://localhost:5173` → 204, allow-origin =
  localhost, max-age 600; from `https://example.com` → 204 without `Access-Control-Allow-Origin`.

| AC | Result | Evidence |
|---|---|---|
| AC-06.1 | pass | own: file read vs spec 06 §Outputs; static test `test_v1_creates_users_exactly_as_spec_06` green. Optional local PG 14 run not done (Docker off); V1 applied on RDS (AC-06.5) |
| AC-06.2 | pass | own: pytest `shared`+`sync` 134 passed (runner order/transactions, gap/duplicate/bad name, checksum, lock, rollback, bad request, IAM token + TLS, dispatch incl. `UNSUPPORTED_EVENT` log line) |
| AC-06.3 | pass | owner screenshot 2026-11-16 (T03-03 Notes): Require TLS enabled, `postgres` secret row IAM authentication **Required**; target Available |
| AC-06.4 | pass | owner: VPC/subnets/SGs and Python 3.12 (T03-03 step 2a, ENVIRONMENT §Compute); role = logs + VPC + inline `rds-db:connect` on `prx-019d0caac664f7be9/postgres` (T03-03 step 3 screenshot); 256 MB / 60 s / env `DB_PROXY_ENDPOINT`,`DB_NAME`,`DB_USER` (ENVIRONMENT §Sync chain, owner screenshots 2026-11-17); code hash `sC61f…F8gs=` = own build |
| AC-06.5 | not verified | owner: `migrate` → `{"applied":[1],"current":1}`, `status` → `{"current":1,"pending":[]}` (T03-03, also re-checked in T03-05 step 4). **Missing:** the second `migrate` result (screenshot sent was the first one again) and the `/aws/lambda/aws-challenge-sync` log lines of the runs |
| AC-06.6 | not verified | own: `git grep` clean. owner: `sync` env + role without Secrets Manager (T03-03, ENVIRONMENT). **Missing (admin part):** `aws-challenge-admin` Environment variables screenshot (exactly the 3 DB vars, no `DB_SECRET_ARN`) and its role policy list incl. inline `aws-challenge-admin-rds-connect`, no `secretsmanager:*` |
| AC-07.1 | pass | own: pytest `post-confirmation` 13 passed |
| AC-07.2 | pass | own: pytest `shared`+`sync` (`test_user_sync.py`: mapping, duplicate → `updated`, height 400 stored, invalid birthdate/height → NULL + `invalidFields`, bad sub/email → `rejected` without DB, DB error raises, SQL parameterised) |
| AC-07.3 | pass | owner screenshots 2026-11-17 (T03-05 Notes, ENVIRONMENT §Sync chain): Classic bus, rule pattern/target `aws-challenge-sync`/1 h/5 retries, Cognito Post confirmation trigger, trigger function no VPC, role inline `events:PutEvents` on the bus + own log streams; sync role `rds-db:connect`, no Secrets Manager (T03-03). Observation: rule has no tags (CLAUDE.md §7, not part of the AC) |
| AC-07.4 | pass | owner Logs Insights 2026-11-17 (T03-05): `published` 11:09:50.905Z, `inserted` 11:09:54.262Z, same `userSub` `12a5c484-…`, ≈3.4 s; row shown in the admin table with all fields (T03-07 Notes, only row, total 1). `durationMs` value and cold-start figure (R-02) not recorded |
| AC-07.5 | waived (owner, 2026-11-17) | T03-05 Notes: back-fill / re-send not done; upsert idempotency covered locally by AC-07.2 (`test_same_event_twice_is_updated_with_one_row`) |
| AC-07.6 | not verified | **Missing:** owner screenshot of the raw post-confirmation and sync log events of the AC-07.4 confirmation (no e-mail, name, birth date, country, height, weight). Supporting only: unit tests assert log lines without values (AC-07.1/07.2) |
| AC-08.1 | pass | own: pytest `shared`+`admin` 104 passed (401 ID token, 403 without DB, each invalid parameter → 400, group formats, empty table, page beyond end, DB error → 500, other route → 404, mapping, sort whitelist, log fields) |
| AC-08.2 | pass | owner screenshot 2026-11-16 (T03-01): group `admin`, 1 member (owner's test account); group in the token proven by "Role: administrator" (T03-07) |
| AC-08.3 | not verified | public probes consistent (`GET /admin`/`POST /chat` 401, `/api/*` 404, `POST /admin` 404, `/unknown` 404; SPA gets 200 via payload-2.0 handler). **Missing:** owner screenshot of the Routes list and of the `GET /admin` route/integration detail (authorizer, `aws-challenge-admin`, payload 2.0) — T03-07 step 4 |
| AC-08.4 | pass | own curl 2026-11-17: 401 / 401 / 404, preflight 204 with allow-origin = Amplify origin (also owner curl, T03-07) |
| AC-08.5 | pass | owner screenshot 2026-11-17 (T03-07): non-admin on deployed SPA, `/admin` → "You do not have access to this page." (state selected only on HTTP 403; handler 403 is always problem+json, AC-08.1). Content type not shown directly |
| AC-08.6 | not verified | owner: SPA admin table 200 via the API (`size=20`); Lambda Test-tab `page=0&size=2` → 200 total 1 (not through the API). **Missing:** T03-07 step 6.2 console output as admin: `/admin?page=0&size=2` 200 `size 2`, items ≤ 2, `total`; `/admin?size=101` 400 `application/problem+json` |
| AC-08.7 | not verified | **Missing:** `/aws/lambda/aws-challenge-admin` retention 2 weeks and the log event of an AC-08.6 request (`route` `GET /admin`, `status` 200, `apiRequestId`, `userSub`; no token/e-mail/profile values) — T03-07 steps 2.6, 6.3 |
| AC-08.8 | not verified | own preflights: origins Amplify + `http://localhost:5173`, max-age 600, foreign origin refused — CORS part **pass**. **Missing:** `aws-challenge-admin` resource-based policy (principal `apigateway.amazonaws.com`, `SourceArn` of `o6cpz238i3`; account id masked) — T03-07 step 4.5 |
| AC-08.9 | not verified | owner: Python 3.12 (ENVIRONMENT §Compute), code hash `2Cu/…H1Ho=` = own working-copy build (clean-checkout caveat above). **Missing:** General configuration (10 s, 256 MB), Environment variables, role policy list with the inline `rds-db:connect` policy — T03-07 steps 1–2 |
| AC-09.1 | pass | own: `npm test` 70 passed (role line admin/other/absent/unreadable, path `/admin?page=<p>&size=20`, paging first/last/`total = 0`, cell formats, state selection); `npm run build` green |
| AC-09.2 | pass | own: `vite preview` + headless Chrome net log (above): no API request, `/admin` placeholder |
| AC-09.3 | pass | owner screenshots 2026-11-17 (T03-07): admin — "Role: administrator", Admin link, table with all columns, "Page 1 of 1 · 1 users"; own: no edit control in `AdminPage.tsx` |
| AC-09.4 | pass | owner screenshots 2026-11-17 (T03-07): non-admin — "Role: user", no Admin link, `/admin` → "You do not have access to this page." |
| AC-09.5 | pass (fallback) | 1 user on `dev` (< 21): verified by the paging unit tests of AC-09.1 (`exactly one full page; 21 users give two pages`, first/middle/last), as the AC allows |
| AC-01.2 | pass | own curl: `/chat` (and `/admin`, `/sign-in`) 200 `text/html`; `/x.js` 404 |

Regressions (TECHNICAL CONSTRAINTS): AC-01.1 pass (own curl: 200, `Via` cloudfront, `X-Cache`, `X-Amz-Cf-Id`);
AC-04.10 pass (= AC-09.2 run); AC-05.3 pass on the routes `/admin`, `/chat` (own curl 401); AC-05.4 `Bearer abc`
pass (own curl); AC-05.2 shares the missing Routes screenshot of AC-08.3.

**Counts:** 27 ACs — 18 pass, 1 waived, 8 not verified, 0 fail.

**Owner checklist — missing evidence** (screenshots, account id masked, no tokens):

1. `aws-challenge-sync` Test tab: `{"action":"migrate"}` once more → `{"applied":[],"current":1}`; CloudWatch
   `/aws/lambda/aws-challenge-sync` log lines of a `migrate` and a `status` run (AC-06.5).
2. `aws-challenge-admin` → Configuration: General configuration (256 MB, 10 s), Environment variables (exactly
   `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_USER`), Permissions → role policy list incl. inline
   `aws-challenge-admin-rds-connect` and its JSON, no `secretsmanager:*` (AC-06.6 admin part, AC-08.9).
3. Raw log events of one confirmation (post-confirmation `published` + sync `inserted`, same `userSub`) — any new
   SPA sign-up + console *Confirm account* is fine (AC-07.6).
4. API Gateway `aws-challenge-api` → Routes list; `GET /admin` route detail and its integration (payload 2.0)
   (AC-08.3, AC-05.2).
5. T03-07 step 6.2 console snippet output as admin (`?page=0&size=2` → 200 …; `?size=101` → 400 problem+json)
   (AC-08.6).
6. `/aws/lambda/aws-challenge-admin`: log group row with retention 2 weeks; the log event of the step-5 call
   (AC-08.7).
7. `aws-challenge-admin` → Configuration → Permissions → Resource-based policy statements (AC-08.8).

**Findings (non-blocking, reported to the owning task):**

- T03-06 / T03-07: deployed `admin` zip is not byte-reproducible from a clean checkout (CRLF in the working copy of
  `lambdas/admin/lambda_function.py`; content identical after LF normalisation). Next `admin` upload: build from an
  LF working copy and record the new hash.
- T03-07: ENVIRONMENT.md §HTTP API still shows the Week 2 CORS (one origin, max age 0) while the live API answers
  for both origins with max age 600 — as-built values not yet recorded (T03-07 scope).
- T03-05: rule `aws-challenge-user-confirmed` has no tags (CLAUDE.md §7); cold-start figure (R-02) not recorded.
- 2026-11-17 (owner): "everything was configured step by step per the runbooks" — the 8 ACs lacking screenshot evidence (AC-06.5 second migrate + sync logs, AC-06.6 admin part / AC-08.9, AC-07.6, AC-08.3, AC-08.6, AC-08.7, AC-08.8 resource-policy half) are **accepted on the owner statement**, backed by the functional end-to-end evidence (admin/non-admin on the deployed SPA, unauthenticated API probes, sync chain logs). Final: 18 pass, 1 waived (AC-07.5), 8 accepted on owner statement, 0 fail → `Review`.
- 2026-11-17: set to `Done` by the owner (Week 3 closed).
