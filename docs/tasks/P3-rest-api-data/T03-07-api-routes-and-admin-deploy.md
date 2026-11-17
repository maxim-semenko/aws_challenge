---
id: T03-07
title: "Admin Lambda deploy, GET /admin route check, CORS (console runbook)"
phase: P3-rest-api-data
status: Done
agent: devops
skills: [cloud-architect, http-api-jwt]
depends_on: [T03-01, T03-03, T03-06]
blocked_by: []
design: ../../design/admin-api.md
spec: [../../specs/06-users-table-and-migrations.md, ../../specs/08-admin-api.md]
acceptance: [AC-06.6, AC-08.3, AC-08.4, AC-08.5, AC-08.6, AC-08.7, AC-08.8, AC-08.9]
---
# T03-07 — Admin Lambda deploy, `GET /admin` route check, CORS (console runbook)

## // BUSINESS CONTEXT

W3-G2, W3-G3, W3-G5, S4: `GET /admin` of the curriculum diagram becomes reachable from the SPA with the contract of
CLAUDE.md §6 (ADR-018, owner 2026-11-17: only `GET /admin` and `POST /chat`, no `/api` routes), and every request is
traceable in the handler log. API access log and throttling: Week 6 (owner, 2026-11-17).

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes; owner evidence without tokens (status codes
  via the browser console snippet pattern of T02-03, adapted to the new paths).
- `aws-challenge-admin`: runtime stays Python 3.12 (ADR-015 revised 2026-11-16; no runtime change), zip from Git (T03-06), timeout 10 s, memory 256 MB, env per spec 06, role
  `rds-db:connect` replaces `secretsmanager:GetSecretValue`; log retention 14 days.
- Routes, permission and CORS exactly design admin-api §3 and spec 08 (ADR-018): exactly `GET /admin` and
  `POST /chat`; explicit methods only (no `ANY`, `OPTIONS`, `$default` — http-api-jwt skill). No access log, no
  throttling in this task (Week 6).
- Tags per CLAUDE.md §7.
- As-built values (proxy resource id, DB user, `DB_NAME`, current `admin` settings and role — facts F1, F3–F5) are
  taken from ENVIRONMENT.md as recorded by T03-03 step 1; if any is missing there, the runbook's first step asks the
  owner to read and report it.

## // SCOPE

**Implement**
- Runbook: admin function update → delete the `/api/...` routes, check `GET /admin` integration (payload 2.0) and the
  resource policy (`SourceArn`) → CORS; verify steps for AC-08.3 … AC-08.9
- ENVIRONMENT.md §HTTP API (routes, integration, CORS) and §Compute (admin settings); skill `http-api-jwt` updated
  (routes)

**Exclude**
- Chat contract (Week 5); API access log and stage throttling (Week 6, owner 2026-11-17); WAF; custom domain; IaC
  (T00-03)

**Interfaces that must match**
- Paths, methods and response contract of spec 08; Amplify `VITE_API_URL` unchanged.

## Definition of Done

- [ ] Runbook executed; AC-08.3 … AC-08.9 evidence in Notes
- [ ] ENVIRONMENT.md and skill updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-18. AC-08.5/08.6 need a non-admin and an admin test account
  (T03-01).
- 2026-11-13: Q-18 A accepted by the owner (ADR-006 revised); design admin-api `Accepted` → `Todo` (waits for
  T03-01, T03-03, T03-06 `Done`).
- 2026-11-16 (devops): status `In progress`; runbook below written. **Gate:** T03-01, T03-03, T03-06 were `Review`
  (ARCH review of T03-06 passed per the coordinator, 2026-11-17). Steps 1–2 (role, configuration) are safe at any time;
  step 3 (upload) and later wait for T03-06 `Done` (or the owner's explicit decision), as in T03-03. Zip checked by
  devops: `build/lambdas/admin.zip` SHA-256 hex `497F819A0DF3AF964B155BA970892B8ACB97BD33F59B47392D0851FC4C45B4DA`
  (= T03-06 value; `lambdas/shared/db.py` unchanged, `e3e71eb0…ff349c`). Reused from ENVIRONMENT.md / T03-03: proxy
  `prx-019d0caac664f7be9`, DB user/name `postgres`/`postgres`, admin VPC config, one console-created role per
  function. Still unknown (read in steps 1–2): the admin role name and policies, current admin memory/timeout/env vars,
  which integration `GET /admin` uses.
- 2026-11-17 (owner screenshots, steps 1–3): role `aws-challenge-admin-role-olbczq73` (created 2026-11-06) has `AWSLambdaBasicExecutionRole-938e2d5f-…` and `AWSLambdaVPCAccessExecutionRole-04ef6ff6-…` (screenshot taken before/without the inline policy — the successful DB call below implies `rds-db:connect` is in place; to confirm). Code SHA-256 `SX+Bmg3zr5ZLFVupcIkrisuXvTP1m0c5LQhR/ExFtNo=` ✔. Test `me-admin` → 200, `Cache-Control: no-store`, groups `["admin"]`, `expiresAt` `2030-01-01T00:00:00Z` ✔. Test `users-admin` (`page=0&size=2`) → 200, `{"items":[1 row],"page":0,"size":2,"total":1}` — admin → RDS Proxy (IAM, TLS) → DB proven ✔.
- 2026-11-17 (owner decision + evidence): routes strictly per the curriculum diagram (ADR-018): `/api/me` and `/api/admin/users` deleted by the owner; remaining `GET /admin` (→ aws-challenge-admin) and `POST /chat`. New admin.zip uploaded — console SHA-256 `2Cu/mq0frEXl1gja/tcfczlSJ/H9FltjW+0awOXH1Ho=` ✔; Test `GET /admin?page=0&size=2` → 200, total 1. Curl (no token): `GET /admin` 401, `POST /chat` 401, `/api/me` 404, `/api/admin/users` 404; preflight `OPTIONS /admin` from the Amplify origin → 204, allow-origin = Amplify, max-age 600. Access log and throttling deferred to Week 6 (owner).
- 2026-11-17 (architect): runbook re-cut to ADR-018 — steps 1–3 done (above; the step 3 hash and test events of the
  `/api` version are superseded by the `GET /admin` zip: hex `d82bbf9a…c7d47a`, base64
  `2Cu/mq0frEXl1gja/tcfczlSJ/H9FltjW+0awOXH1Ho=`; built from a working copy with CRLF in
  `lambdas/admin/lambda_function.py`, so a rebuild from a clean checkout of `faf7a15` gives a different hash — recorded
  in T03-06); step 4 = route clean-up and checks, step 5 = CORS only, step 6 = verification on `/admin`. Already
  evidenced: AC-08.4 (curl). Still open: step 4 screenshots (AC-08.3, resource policy), step 5 CORS page (AC-08.8),
  step 6.2 / 6.3 (AC-08.5, AC-08.6, AC-08.7), inline policy screenshot (AC-08.9, AC-06.6).

## Runbook (owner executes in the AWS console, region **eu-west-1 / Europe (Ireland)**)

| Placeholder | Value |
|---|---|
| API | `aws-challenge-api` (id `o6cpz238i3`), stage `$default`, endpoint `https://o6cpz238i3.execute-api.eu-west-1.amazonaws.com` |
| Authorizer | `cognito-jwt-authorizer` (id `fvppl3`) — reused, not changed |
| Amplify origin | `https://main.d67fa9mmezz1k.amplifyapp.com` |
| Proxy endpoint / DB name / DB user | `proxy-1793961665875-aws-challenge-db.proxy-cbk4syqsq9pn.eu-west-1.rds.amazonaws.com` / `postgres` / `postgres` |
| Tags | `project` = `aws-challenge`, `env` = `dev`, `owner` = `max` |
| `<ACCOUNT_ID>` | 12 digits, console top right → account menu → Account ID. Paste only into the IAM / Lambda / API Gateway fields below; mask it in every screenshot |

### Step 1 — Role of `aws-challenge-admin` (IAM; 5 min)

1. Lambda → `aws-challenge-admin` → **Configuration → Permissions** → click the role name (`aws-challenge-admin-role-…`)
   → IAM, tab **Permissions**. Expected (as for sync): `AWSLambdaBasicExecutionRole-<uuid>` and
   `AWSLambdaVPCAccessExecutionRole-<uuid>` (customer managed, console-created in Week 1). Open the VPC one → **JSON**:
   it must contain `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface`. If no
   such policy exists: **Add permissions → Attach policies** → `AWSLambdaVPCAccessExecutionRole` (AWS managed).
2. **Add permissions → Create inline policy → JSON** → replace everything with:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "ConnectToRdsProxyAsPostgres",
         "Effect": "Allow",
         "Action": "rds-db:connect",
         "Resource": "arn:aws:rds-db:eu-west-1:<ACCOUNT_ID>:dbuser:prx-019d0caac664f7be9/postgres"
       }
     ]
   }
   ```

   **Next** → name `aws-challenge-admin-rds-connect` → **Create policy**.
3. Final list exactly: the logs policy, the VPC policy, inline `aws-challenge-admin-rds-connect`. Detach anything with
   `secretsmanager:*` or other services (AC-06.6). Tab **Tags**: add missing `project` / `env` / `owner`.
- **Report:** role name; screenshot of the policy list; inline JSON (account id masked); whether the VPC policy existed.

### Step 2 — Configuration of `aws-challenge-admin` (Lambda; 5 min)

1. **Configuration → General configuration → Edit**: Memory **256** MB, Ephemeral storage 512 MB (unchanged),
   SnapStart None, Timeout **0 min 10 sec**, role unchanged → **Save**.
2. **Environment variables → Edit**: exactly these three; **remove** every other variable (e.g. a Week 1 DB host or
   `DB_SECRET_ARN`); do not add `AWS_REGION` (set by the runtime):

   | Key | Value |
   |---|---|
   | `DB_PROXY_ENDPOINT` | `proxy-1793961665875-aws-challenge-db.proxy-cbk4syqsq9pn.eu-west-1.rds.amazonaws.com` (host only, not the instance endpoint) |
   | `DB_NAME` | `postgres` |
   | `DB_USER` | `postgres` |

3. **VPC**: no change; check `aws-challenge-vpc`, subnets `subnet-0158cc34af19a05c3`, `subnet-0686f4fa10f9d139a`, SGs
   `sg-01f3496b63a8a0e7e`, `sg-09356f785149eeb60`.
4. **Code → Runtime settings**: Python 3.12, handler **`lambda_function.lambda_handler`** (set it if it differs),
   x86_64.
5. **Configuration → Tags**: `project` / `env` / `owner`.
6. CloudWatch → **Log groups** → `/aws/lambda/aws-challenge-admin` → **Actions → Edit retention setting → 2 weeks
   (14 days)**; its Tags tab → the three tags.
- **Report:** screenshots of General configuration, Environment variables, VPC, Runtime settings, the log group row
  (*Retention 2 weeks*).

### Step 3 — Upload the code and smoke-test (gate: T03-06 `Done`; 10 min)

> **Done 2026-11-17 (Notes).** The text below is the first (`/api`) version, kept as executed. The deployed zip is now
> the `GET /admin` version: Code SHA256 `2Cu/mq0frEXl1gja/tcfczlSJ/H9FltjW+0awOXH1Ho=` (hex `d82bbf9a…c7d47a`);
> a repeat smoke test uses `routeKey` `GET /admin`, `rawPath` / `http.path` `/admin`, `rawQueryString`
> `page=0&size=2` (expected 200 `{"items":[…],"page":0,"size":2,"total":<rows>}`).

1. PowerShell in the repository root:

   ```powershell
   py -3.13 lambdas/package.py admin
   Get-FileHash build\lambdas\admin.zip -Algorithm SHA256
   ```

   Expected `admin.zip: 90 files`, hash `497F819A0DF3AF964B155BA970892B8ACB97BD33F59B47392D0851FC4C45B4DA`. Different
   hash → stop, ask devops (no unrecorded zip).
2. Lambda → `aws-challenge-admin` → **Code → Upload from → .zip file** → `build\lambdas\admin.zip` → **Save**. Never
   use the inline editor's *Deploy* (R-15). *Code properties* → SHA256 = `SX+Bmg3zr5ZLFVupcIkrisuXvTP1m0c5LQhR/ExFtNo=`.
3. **Test** → *Create new event* → name `me-admin`, *Private*, replace the template with (fictitious claims; API
   Gateway delivers claims as strings) → **Save** → **Test**:

   ```json
   {
     "version": "2.0",
     "routeKey": "GET /api/me",
     "rawPath": "/api/me",
     "rawQueryString": "",
     "headers": {},
     "requestContext": {
       "requestId": "console-test-0001",
       "routeKey": "GET /api/me",
       "http": { "method": "GET", "path": "/api/me" },
       "authorizer": { "jwt": { "claims": {
         "sub": "00000000-0000-0000-0000-000000000001",
         "username": "00000000-0000-0000-0000-000000000001",
         "token_use": "access",
         "cognito:groups": "[admin]",
         "exp": "1893456000"
       }, "scopes": null } }
     },
     "isBase64Encoded": false
   }
   ```

   Expected: `statusCode` 200, header `Cache-Control: no-store`, body
   `{"id":"00000000-0000-0000-0000-000000000001","username":"00000000-0000-0000-0000-000000000001","groups":["admin"],"expiresAt":"2030-01-01T00:00:00Z"}`.
4. Second event `users-admin`: copy of the first with `routeKey` `GET /api/admin/users` (both places), `rawPath` and
   `http.path` `/api/admin/users`, `rawQueryString` `page=0&size=2`, `requestId` `console-test-0002` → **Test**.
   Expected 200, body `{"items":[…],"page":0,"size":2,"total":<rows in users>}` — proves admin → proxy (IAM, TLS) →
   DB. A 500 problem+json → Troubleshooting (handler log `errorClass`).
5. **Monitor → View CloudWatch logs**: one JSON line per test (`"route":"GET /api/me","status":200,"outcome":"success"`,
   `apiRequestId` `console-test-0001`), no token, e-mail or names.
- **Report:** package/hash output; *Code properties*; both test results (blur the `items` array — real user data);
  the two log lines.

### Step 4 — Routes, integration, permission (API Gateway + Lambda; 10 min)

ADR-018: the API keeps exactly the curriculum diagram's routes `GET /admin` and `POST /chat`. API Gateway → **APIs**
→ `aws-challenge-api`.

1. **Develop → Routes**: delete `GET /api/me` and `GET /api/admin/users` (**done by the owner 2026-11-17**). The list
   is exactly `GET /admin` and `POST /chat`; no `ANY`, `OPTIONS`, `$default` or `/api/...` route.
2. Select `GET /admin` → *Authorization*: `cognito-jwt-authorizer` (JWT), no authorization scopes. Same check for
   `POST /chat`.
3. **Develop → Integrations** → `GET /admin` → integration detail: target Lambda `aws-challenge-admin` (eu-west-1),
   **Payload format version 2.0**. If it shows 1.0: **Manage integration → Edit → Advanced settings → 2.0 → Save**
   (the handler reads payload v2 only). Note the integration id. `POST /chat` keeps integration `dyujbqp` (Week 5).
   Integrations without a route (e.g. the one created for the `/api` routes) may be deleted under *Manage integrations*.
4. **Deploy → Stages → `$default`**: *Automatic deployment* **enabled** (if not: **Deploy** → stage `$default`).
5. Lambda → `aws-challenge-admin` → **Configuration → Permissions → Resource-based policy statements**: every
   statement must have principal `apigateway.amazonaws.com`, action `lambda:InvokeFunction` and a `SourceArn` of this
   API (`arn:aws:execute-api:eu-west-1:<ACCOUNT_ID>:o6cpz238i3/…`, e.g. `…/*/*/admin`). Delete statements whose
   `SourceArn` names an `/api/...` path or another API, and any statement without `SourceArn`. If no statement is left
   for `/admin`: **Add permissions** → *AWS service* → **API Gateway**; Statement ID `aws-challenge-api-invoke`; Source
   ARN `arn:aws:execute-api:eu-west-1:<ACCOUNT_ID>:o6cpz238i3/*/*/admin`; Action `lambda:InvokeFunction` → **Save**.
- **Report:** Routes list; `GET /admin` route detail (authorizer, integration); the integration detail (payload 2.0);
  the resource policy JSON (account id masked).

### Step 5 — CORS (5 min)

API access log and stage throttling are **not** part of this task (Week 6, owner 2026-11-17).

1. **Develop → CORS → Configure**: Allow-Origin `https://main.d67fa9mmezz1k.amplifyapp.com` **and**
   `http://localhost:5173` (**Add**); Allow-Headers `authorization`, `content-type` (unchanged); Allow-Methods
   unchanged (`*`); Expose-Headers empty; Max-Age **600**; Allow-Credentials **NO** → **Save**.
- **Report:** screenshot of the CORS page (both origins, max age 600). The 2026-11-17 preflight already shows max age
  600; the screenshot proves the localhost origin.

### Step 6 — Verification (owner; 10 min; never print or screenshot a token)

1. **No token / preflight (AC-08.4)** — **done 2026-11-17** (Notes: `GET /admin` 401, `POST /chat` 401, `/api/me` 404,
   `/api/admin/users` 404, preflight 204, max age 600). Repeat only after a change:

   ```powershell
   $api = 'https://o6cpz238i3.execute-api.eu-west-1.amazonaws.com'
   curl.exe -s -o NUL -w "%{http_code}`n" "$api/admin"
   curl.exe -s -o NUL -w "%{http_code}`n" -X POST "$api/chat"
   curl.exe -s -o NUL -w "%{http_code}`n" "$api/api/me"
   curl.exe -i -X OPTIONS "$api/admin" -H "Origin: https://main.d67fa9mmezz1k.amplifyapp.com" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization"
   ```

   Expected: `401`, `401`, `404`; preflight `204` with `access-control-allow-origin:
   https://main.d67fa9mmezz1k.amplifyapp.com` and `access-control-max-age: 600`.
2. **With a token (AC-08.5, AC-08.6)**: deployed SPA, signed in, DevTools → **Console**, paste. Prints only status
   codes and counts — never the token or user data:

   ```js
   const api = 'https://o6cpz238i3.execute-api.eu-west-1.amazonaws.com'
   const pre = 'CognitoIdentityServiceProvider.384mpdjvmjpb1s9ddqjcbg79hg'
   const t = localStorage.getItem(pre + '.' + localStorage.getItem(pre + '.LastAuthUser') + '.accessToken')
   const call = async (path) => {
     const r = await fetch(api + path, { headers: { Authorization: 'Bearer ' + t } })
     const b = await r.json().catch(() => null)
     console.log(path, r.status, r.headers.get('content-type'),
       b?.items ? { page: b.page, size: b.size, total: b.total, items: b.items.length } : b?.title)
   }
   await call('/admin?page=0&size=2'); await call('/admin?size=101')
   ```

   - **Admin** (`test@gmail.com`; sign out and in again so the token carries the group): `?page=0&size=2` 200
     `size: 2`, `items` ≤ 2, `total` = rows in `users`; `?size=101` 400 `application/problem+json` `Bad Request`.
   - **Non-admin** (any confirmed user not in `admin`; sign up and confirm one if needed — cognito-user-pool skill):
     both calls 403 `application/problem+json` `Forbidden`.
3. **Handler log (AC-08.7)**: CloudWatch → `/aws/lambda/aws-challenge-admin` (retention 2 weeks) → **Search log
   group** `"GET /admin"` → the line of the admin's `?page=0&size=2` call: `"route":"GET /admin"`, `"status":200`,
   `apiRequestId` and `userSub` set; no token, e-mail or profile value.
- **Report:** console output for both users; the log event (screenshot).

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| 500 `{"message":"Internal Server Error"}` | resource policy missing / wrong `SourceArn` | step 4.5 |
| 404 `{"message":"Not Found"}` on `/admin` | route missing or stage not deployed | steps 4.1, 4.4 |
| 401 `{"message":"Unauthorized"}` with a token | token expired or from another pool | sign in again |
| 401 problem+json (handler) | ID token sent (`token_use` ≠ `access`) | the snippet must read `.accessToken` |
| 403 for the admin | token issued before the group membership | sign out, sign in |
| 404 problem+json (handler) | integration payload 1.0 (no `routeKey`) | step 4.3 |
| 500 problem+json, `errorClass` in the handler log | DB path: env vars, inline policy ARN, SG (as T03-03 Troubleshooting) | steps 1.2, 2.2, 2.3 |
| `Task timed out after 3.00 seconds` | timeout not saved | step 2.1 |
| CORS error only from `localhost:5173` | origin not added | step 5.1 |

### Rollback

- API: routes stay (`GET /admin`, `POST /chat` are the Week 2 routes); CORS without `http://localhost:5173`, max age 0.
- Lambda: the Week 1 probe code is not in Git (R-15) and cannot be restored; re-upload an earlier Git zip if a later
  one breaks.
- Role: delete inline `aws-challenge-admin-rds-connect`; memory/timeout/env vars back to the step 2 screenshots.

### Verify / evidence per AC

| AC | Evidence (account id masked, no tokens) |
|---|---|
| AC-06.6 (admin part) | steps 1, 2: no `DB_SECRET_ARN`, password or `secretsmanager:*` (inline policy screenshot still open) |
| AC-08.3 | step 4 Routes list and route details |
| AC-08.4 | step 6.1 output (received 2026-11-17) |
| AC-08.5, AC-08.6 | step 6.2 console output (non-admin, admin) |
| AC-08.7 | step 6.3 log event; retention from step 2.6 |
| AC-08.8 | step 5.1 CORS, step 4.5 resource policy |
| AC-08.9 | steps 1–3: Python 3.12, 10 s, 256 MB, env vars, role, Code SHA256 `2Cu/mq0frEXl1gja/tcfczlSJ/H9FltjW+0awOXH1Ho=` (received 2026-11-17) |

Afterwards devops records the as-built values in ENVIRONMENT.md (§HTTP API routes, `GET /admin` integration id,
CORS; §Compute admin settings and role) and updates the `http-api-jwt` skill.

### Cost

No new always-on resource → **$0/month** extra. HTTP API ≈ $1 per million requests; handler log ingestion and storage
at learning volume ≈ $0 with 14-day retention; 256 MB × ≤ 10 s per call stays in the free tier; IAM and resource
policies are free. Proxy and DB cost unchanged.
- 2026-11-17 (owner screenshots, deployed SPA after push 66be514): **admin** `test@gmail.com` — profile "Role: administrator", nav shows Admin, `/admin` page shows the users table (1 row `test4@gmail.com`, all fields, "Page 1 of 1 · 1 users") → `GET /admin` 200 through the API; **non-admin** `test4@gmail.com` — profile "Role: user", no Admin link, direct `/admin` → "You do not have access to this page." (403 from the API). CORS: preflight max-age 600 observed by curl (localhost origin not screenshotted).
- 2026-11-17: set to `Done` by the owner (Week 3 closed).
