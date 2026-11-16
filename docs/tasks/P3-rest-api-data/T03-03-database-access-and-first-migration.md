---
id: T03-03
title: "RDS Proxy IAM authentication, sync function DB configuration and first migration via sync (console runbook)"
phase: P3-rest-api-data
status: Review
agent: devops
skills: [cloud-architect, postgres-pro]
depends_on: [T03-02]
blocked_by: []
design: ../../design/user-sync.md
spec: ../../specs/06-users-table-and-migrations.md
acceptance: [AC-06.3, AC-06.4, AC-06.5, AC-06.6]  # AC-06.6: the sync part; admin part in T03-07
---
# T03-03 — RDS Proxy IAM authentication, sync DB configuration and first migration via sync

## // BUSINESS CONTEXT

W3-G1, S1, S5: the users table must exist in RDS before anything can be synced or listed, and the VPC functions need
a way to reach the database without NAT and without secrets in code (R-09, Q-18). Re-scoped 2026-11-16 (owner): there
is no migrate function — `aws-challenge-sync` gets its database configuration here and runs the first migration from
its Test tab (ADR-017 revised).

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes with exact values; the owner executes and
  reports identifiers/screenshots (account id masked).
- **Prerequisite (runbook step 1, owner evidence — not a blocker):** the owner reads and reports the as-built facts
  below (screenshots, no secret values, account id masked); they are recorded in ENVIRONMENT.md and fill in the
  values of the later steps (`<prx-id>`, `<db user>`, `DB_NAME`, subnets, security group). T03-05 and T03-07 reuse
  them from ENVIRONMENT.md. If a fact contradicts design user-sync §1 (e.g. the proxy cannot require IAM auth for its
  user), stop after step 1 and report to ARCH.

  | # | Fact | Where in the console |
  |---|---|---|
  | F1 | How the Week 1 `admin` probe obtains the DB password (Secrets Manager call, env var, hard-coded?) and which driver it uses | Lambda → `aws-challenge-admin` → Code, Configuration → Environment variables (names only) |
  | F2 | Whether any NAT gateway or interface VPC endpoint exists | VPC → NAT gateways; VPC → Endpoints |
  | F3 | The subnets and security group of each function | Lambda → each function → Configuration → VPC |
  | F4 | RDS Proxy: resource id (`prx-…`), IAM authentication setting, registered secret, DB user name, `DB_NAME` | RDS → Proxies → the proxy |
  | F5 | Runtime, architecture, memory, timeout, role name of `admin` and `sync` | Lambda → Configuration → General, Permissions |
- Proxy: IAM authentication **required** for the registered DB user and **Require TLS** on; record the proxy resource
  id (`prx-…`) and the DB user in ENVIRONMENT.md.
- **No function `aws-challenge-migrate`** (owner, 2026-11-16): no new function, role or log group for migrations.
- Function `aws-challenge-sync` (exists): runtime **stays Python 3.12** (no runtime change, ADR-015 revised); VPC =
  private subnets + the Lambda security groups as built (ENVIRONMENT.md §Compute; no `sg-lambda` exists); timeout
  **60 s**; memory 256 MB; env vars exactly `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_USER` (spec 06; remove any other,
  e.g. `DB_SECRET_ARN`); role: `AWSLambdaVPCAccessExecutionRole` (or equivalent VPC + logging) + inline
  `rds-db:connect` on `arn:aws:rds-db:eu-west-1:<account>:dbuser:<prx-id>/<db user>` only, no Secrets Manager or other
  permission. If the as-built role is shared with another function, create a dedicated `aws-challenge-sync-role`
  instead of editing the shared one (one role per function, ARCHITECTURE §0). Log group `/aws/lambda/aws-challenge-sync`
  retention 14 days; tags `project`, `env`, `owner` (CLAUDE.md §7).
- Needs the sync part of F5 (role name and its policies, timeout, memory, architecture, env var names, log group
  retention) — the owner reports it first if not yet in ENVIRONMENT.md.
- Code only from the `sync` zip built by T03-02 (no console edits, R-15). The `UserConfirmed` upsert arrives later
  (T03-04 → T03-05); until then an EventBridge event would get `UNSUPPORTED_EVENT` — no rule targets `sync` yet.

## // SCOPE

**Implement**
- Runbook: step 1 pre-check (done 2026-11-16); step 2 proxy IAM auth + TLS; sync configuration (timeout, env vars,
  role, log retention); upload the T03-02 `sync` zip; Test-tab `status`, `migrate`, `migrate` again, `status`;
  verify steps for AC-06.3 … AC-06.6 (sync part)
- Record identifiers in ENVIRONMENT.md ("Database access (Week 3)" section; proxy IAM/TLS setting, sync settings and
  role; facts F1–F5)
- Update skill `postgres-migrations` (observed outputs of the owner's run)

**Exclude**
- `admin` (T03-07); EventBridge, trigger and the upsert code upload (T03-05); NAT or endpoints (not needed with
  Q-18 A); any migrate function

**Interfaces that must match**
- Env var names, dispatch, results and log line as spec 06; function name `aws-challenge-sync`.

## Definition of Done

- [ ] Runbook executed; AC-06.3 … AC-06.5 and AC-06.6 (sync part) evidence in Notes
- [ ] ENVIRONMENT.md and skill updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-16 and Q-18.
- 2026-11-13: Q-16 A and Q-18 A accepted by the owner (ADR-017, ADR-006 revised); design user-sync `Accepted` →
  `Todo` (waits for T03-02 `Done`). The Q-18 facts F1–F5 moved here from RISKS.md as runbook step 1.
- 2026-11-16 (owner, F1): the Week 1 `admin` probe is a plain TCP check (`socket.connect` to port 5432, 5 s
  timeout), not `SELECT 1`: no driver, no password, no Secrets Manager call. Its host is
  `aws-challenge-db.cbk4syqsq9pn.eu-west-1.rds.amazonaws.com` — a **DB instance endpoint**, not an RDS Proxy endpoint
  (proxy endpoints have the form `<name>.proxy-<id>.<region>.rds.amazonaws.com`). So Week 1 proved only that the
  private subnets reach the instance on 5432; neither authentication nor the path through the proxy has been proven.
  This task's first migration through the proxy with IAM auth is the first real end-to-end DB check. Step 1 of the
  runbook must also record the proxy endpoint (F4) and confirm the proxy's security group allows the Lambdas' SG.
  R-09 open point closed: no AWS API is called from the VPC today.
- 2026-11-16 (owner screenshots; F3/F4 partly): proxy target `aws-challenge-db` is **Unavailable**. Cause: the
  proxy, the Lambdas and (assumed) the DB instance share `aws-challenge-db-sg`, whose only inbound rule allows TCP
  5432 from one external IP (`185.53.96.139/32`) — neither proxy → DB nor Lambda → proxy is allowed. The Week 1 TCP
  probe reached the instance only through the default SG (all traffic from itself), which the proxy does not have.
  Fix given to the owner: add a self-referencing inbound rule on `aws-challenge-db-sg` (TCP 5432, source
  `sg-01f3496b63a8a0e7e`); then the target must turn Available. Also: the functions run Python 3.12, not 3.13
  (ADR-015) — switch the runtime when deploying from Git. Values in ENVIRONMENT.md.
- 2026-11-16 (owner): self-referencing rule added to `aws-challenge-db-sg`; proxy target group `default` → `aws-challenge-db` now **Available** (screenshot). Proxy → DB path proven at the proxy level; Lambda → proxy → DB with IAM auth is proven by this task.
- 2026-11-16 (devops): status `In progress`; runbook below written. Facts F1, F3, F4 recorded (ENVIRONMENT.md);
  F2 is not needed by this task (the IAM token is signed locally, `migrate` calls no AWS API from the VPC) and stays
  an open line in ENVIRONMENT.md; F5 belongs to T03-05/T03-07. **Gate:** T03-02 is `Review`, not `Done` — the owner
  executes steps 1–5 any time, but step 6 (upload) only after T03-02 is `Done` (or with the owner's explicit
  decision to upload the reviewed-pending code). Zip built locally by devops 2026-11-16: `build/lambdas/migrate.zip`,
  91 files, 430 982 bytes, SHA-256 hex `D5257298E8CF5F8416AF8A56204C202754EBA92CEEBCBCBD442B9883A0EE3A37` (base64
  as Lambda shows it: `1SVymOjPX4QWr4pWIEwgJ1TrqSzuvLy9RCuYg6DuOjc=`; rebuilt by backend 2026-11-16 after the T03-02 review fixes). pytest of `lambdas/shared` + `lambdas/migrate`
  not run by devops (no venv) — not verified here, it is T03-02's invariant.
- 2026-11-16 (ARCH, owner decisions): **re-scoped.** (1) No function `aws-challenge-migrate` — the runner is part of
  `aws-challenge-sync` (ADR-017 revised, Q-16 amended); old steps 3–5 (migrate log group, role, function) were **not
  executed** by the owner and are **dropped**; the `migrate.zip` hash above is obsolete — T03-02 rebuilds as
  `sync.zip`. (2) Runtime stays Python 3.12 (ADR-015 revised) — the "switch the runtime" remark above is withdrawn.
  (3) **Step 1 done** (owner evidence 2026-11-16): `aws-challenge-db-sg` outbound = all traffic to `0.0.0.0/0`
  (recorded in ENVIRONMENT.md). (4) Step 2 (proxy) unchanged and executable now. (5) Steps 3–6 below are an outline:
  devops writes the exact console values once the owner has reported the sync part of F5; step 4 (upload) waits for
  T03-02 `Done`. AC-06.6 (sync part) moved here from T03-05, since this task now configures `sync`.
- 2026-11-16 (backend, T03-02 rework): `py -3.13 lambdas/package.py sync` → `build/lambdas/sync.zip`, **92 files,
  431 888 bytes**, SHA-256 hex `08D77249F1170D315F3B05AD9C77D3A24E5E740CEBEB55FD5B9D9B4780C73DC4`, base64 as Lambda's
  *Code SHA256* shows it: `CNdySfEXDTFfOwWtnHfTok5edAzr61X9W52bR4DHPcQ=`; identical on rebuild. Valid only for the
  current Git state of `lambdas/sync` + `lambdas/shared`; T03-02 still `Review` (ARCH re-review), so the step-4 gate
  stands. `build/lambdas/migrate*` deleted.
- 2026-11-16 (owner, step 2a): `aws-challenge-sync` — memory 128 MB, ephemeral 512 MB, timeout 3 s, SnapStart none;
  no environment variables; Python 3.12, x86_64, handler `lambda_function.lambda_handler`, runtime updates Auto,
  no layers, package 299 bytes (Week 1 placeholder); role `aws-challenge-sync-role-q8b1jajy` (console-created,
  own role per function) whose resource summary shows only `AWSLambdaBasicExecutionRole-…` (CloudWatch Logs:
  CreateLogGroup on the account, CreateLogStream/PutLogEvents on `/aws/lambda/aws-challenge-sync:*`). Owner: all
  three functions were configured the same way in Week 1 (each with its own console-created role).
- 2026-11-16 (owner, step 2 partial): Require TLS ticked in the Modify form; IAM authentication still *Not allowed*
  there — not yet verified on the proxy details page (ENVIRONMENT.md unchanged until then).
- 2026-11-16 (devops): steps 3–6 written with exact console values (outline replaced; this note moved here from
  below the Cost section). Role not shared → edited in place. The role shows no EC2 ENI permissions although `sync`
  is VPC-attached; step 3.1–3.2 has the owner check and attach `AWSLambdaVPCAccessExecutionRole` if missing. Upload
  is now step 5 (gate T03-02 `Done` unchanged); Test-tab invokes step 6. Expected zip hash = backend's 2026-11-16
  `sync.zip` value above.

## Runbook (owner executes in the AWS console, region **eu-west-1 / Europe (Ireland)**)

Values used below (homes: ENVIRONMENT.md §Database, §Compute):

| Placeholder | Value |
|---|---|
| Proxy name | `proxy-1793961665875-aws-challenge-db` (resource id `prx-019d0caac664f7be9`) |
| Proxy endpoint | `proxy-1793961665875-aws-challenge-db.proxy-cbk4syqsq9pn.eu-west-1.rds.amazonaws.com` |
| DB user / DB name | `postgres` / `postgres` |
| Private subnets | `subnet-0158cc34af19a05c3`, `subnet-0686f4fa10f9d139a` |
| Security groups | `sg-01f3496b63a8a0e7e` (`aws-challenge-db-sg`), `sg-09356f785149eeb60` (default) — same pair as the other functions; only `aws-challenge-db-sg` is needed for the proxy |
| Tags (every resource created here) | `project` = `aws-challenge`, `env` = `dev`, `owner` = `max` |
| `<ACCOUNT_ID>` | 12-digit account id: console top-right → account name menu → **Account ID** (copy icon, no dashes). Paste it **only** into the IAM policy editor; never into the repo, chat or screenshots (mask it) |

**Nothing existing breaks.** No client uses the proxy today: the Week 1 `admin` probe is a TCP connect to the
**instance** endpoint (F1), it sends no password and does not touch the proxy, so it keeps working after step 2. After
step 2 password logins **through the proxy** are rejected (none exist). The proxy keeps its secret towards the DB.

### Step 1 — Pre-check (2 min) — DONE 2026-11-16 (outbound all traffic to 0.0.0.0/0)

1. EC2 → Security Groups → `aws-challenge-db-sg` (`sg-01f3496b63a8a0e7e`) → tab **Outbound rules**.
2. Expected: a rule that allows TCP 5432 (or All traffic) to `0.0.0.0/0` or to `sg-01f3496b63a8a0e7e`. If there is
   none, stop and report (Lambda → proxy would be blocked).
- **Report:** screenshot of the Outbound rules tab.

### Step 2 — RDS Proxy: IAM authentication Required + Require TLS (AC-06.3)

**Status 2026-11-16 (owner):** Require TLS ticked; the secret row still showed **IAM authentication: Not allowed** in
the edit form. Set it to **Required** (2.3) in the same *Modify* — or open *Modify* again if already saved — and check
the result on the proxy **details page**, not in the form. Steps 3–4 can run meanwhile; step 6 needs step 2 done.

1. RDS → **Proxies** → `proxy-1793961665875-aws-challenge-db` → **Modify** (top right).
2. Section **Connectivity**: tick **Require Transport Layer Security** (IAM auth to RDS Proxy works only over TLS;
   our code always uses verified TLS; this makes plain-text connections impossible for any client).
3. Section **Authentication** (on some console versions under **Additional configuration**), row of the secret
   `rds-db-credentials/…/postgres`: **IAM authentication** → **Required**. Leave **Client authentication type**
   (SCRAM SHA 256), the secret, the IAM role `rds-proxy-role-1793961664993`, idle timeout and everything else
   unchanged. If the console offers a "default authentication scheme" / end-to-end IAM option, leave it as is (none).
4. **Modify proxy** / **Continue**. Wait until the proxy status is **Available** again (1–5 min); Targets:
   `aws-challenge-db` still **Available**.
- **Report:** screenshot of the proxy details page showing *Require TLS: enabled* and the Authentication row with
  *IAM authentication: Required*; screenshot of Targets (Available).

### Step 2a — Report the sync facts (F5, sync part; 3 min, read-only) — DONE 2026-11-16 (Notes, ENVIRONMENT.md §Compute)

Lambda → `aws-challenge-sync` → **Configuration**: screenshots of *General configuration* (memory, timeout, ephemeral
storage), *Environment variables* (names; mask any value that looks like a secret), *VPC*, *Permissions* (role name;
open the role and screenshot its policy list), *Monitoring and operations tools → Logging configuration* (log group,
format); **Code → Runtime settings** (runtime, handler, architecture). Also: is the same role attached to `admin` or
`chatbot`? (IAM → the role → *Last activity* is not enough — compare the role name on each function's Permissions tab.)
devops then writes steps 3–6 with exact values.

The role is not shared (step 2a: one console-created role per function), so it is edited in place — no new role.

### Step 3 — Role `aws-challenge-sync-role-q8b1jajy` (IAM; 5 min)

1. IAM → **Roles** → search `aws-challenge-sync-role-q8b1jajy` → tab **Permissions**. Expected today: one policy
   `AWSLambdaBasicExecutionRole-<uuid>` (customer managed, logs). Click each listed policy → **JSON**: look for
   `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface`. (Quick view: Lambda →
   `aws-challenge-sync` → Configuration → **Permissions** → *Resource summary* drop-down — an **Amazon EC2** entry
   means the ENI permissions exist; only *Amazon CloudWatch Logs* means they are missing.)
2. If the EC2 permissions are missing: **Add permissions → Attach policies** → search `AWSLambdaVPCAccessExecutionRole`
   → tick the one of type *AWS managed* → **Add permissions**. Why: Lambda uses this role to create/delete the
   function's ENIs in the private subnets; without it a later config change or the reactivation of an idle VPC
   function fails (*"The provided execution role does not have permissions to call CreateNetworkInterface on EC2"*).
   This AWS managed policy is the accepted exception to "no wildcard resources" (task constraints; EC2 ENI actions
   cannot be scoped to a resource). Keep `AWSLambdaBasicExecutionRole-<uuid>`.
3. **Add permissions → Create inline policy** → **JSON** → replace everything with (paste your account id in place of
   `<ACCOUNT_ID>`, 12 digits, only here):

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

   **Next** → Policy name `aws-challenge-sync-rds-connect` → **Create policy**. (`prx-…` is the proxy resource id, not
   the DB instance; `postgres` is the DB user.)
4. Final list must be exactly: `AWSLambdaBasicExecutionRole-<uuid>`, `AWSLambdaVPCAccessExecutionRole` (or an existing
   policy with the three EC2 actions), inline `aws-challenge-sync-rds-connect`. Nothing with `secretsmanager:*`
   (detach it if present).
5. Tab **Tags** → add any missing: `project` = `aws-challenge`, `env` = `dev`, `owner` = `max`.
- **Report:** screenshot of the Permissions tab (policy list); screenshot of the inline policy JSON with the account
  id masked; what step 3.1 showed (EC2 present or attached now).

### Step 4 — Function configuration `aws-challenge-sync` (Lambda; 5 min)

1. Lambda → Functions → `aws-challenge-sync` → **Configuration** → **General configuration** → **Edit**: Memory
   **256** MB; Ephemeral storage **512** MB (unchanged); SnapStart **None**; Timeout **1** min **0** sec; Execution
   role *Use an existing role* `aws-challenge-sync-role-q8b1jajy` (unchanged) → **Save**.
2. **Environment variables** → **Edit** → **Add environment variable** three times, nothing else (`AWS_REGION` is set
   by the runtime — do not add it):

   | Key | Value |
   |---|---|
   | `DB_PROXY_ENDPOINT` | `proxy-1793961665875-aws-challenge-db.proxy-cbk4syqsq9pn.eu-west-1.rds.amazonaws.com` (host only: no `https://`, no `:5432`, no spaces; **not** the instance endpoint `aws-challenge-db.cbk4…`) |
   | `DB_NAME` | `postgres` |
   | `DB_USER` | `postgres` |

   Leave *Encryption configuration* as is (no customer KMS key) → **Save**.
3. **VPC**: no change; check it still shows `aws-challenge-vpc`, subnets `subnet-0158cc34af19a05c3`,
   `subnet-0686f4fa10f9d139a`, security groups `sg-01f3496b63a8a0e7e`, `sg-09356f785149eeb60`. If a Save in 4.1/4.2
   failed with a *CreateNetworkInterface* error → step 3.2.
4. **Code** tab → **Runtime settings**: Python 3.12, handler `lambda_function.lambda_handler`, architecture x86_64 —
   no change (the zip is pure Python, so the architecture does not matter; keep as built).
5. **Configuration → Tags** → **Manage tags** → add any missing `project` / `env` / `owner` (values as in the table
   above).
6. CloudWatch → **Log groups** → `/aws/lambda/aws-challenge-sync` → **Actions → Edit retention setting** → **2 weeks
   (14 days)** → **Save**; its **Tags** tab → the same three tags. If the log group does not exist yet (function never
   invoked), do this after the first invoke in step 6.
- **Report:** screenshots of General configuration, Environment variables (the values are not secret), VPC, Runtime
  settings, Tags; the log group row showing *Retention 2 weeks*.

### Step 5 — Upload the code (gate: T03-02 `Done`; 5 min)

Do not start before T03-02 is `Done` (ARCH re-review in progress), unless you decide explicitly to upload the
review-pending code.

1. PowerShell in the repository root, on the reviewed Git state:

   ```powershell
   py -3.13 lambdas/package.py sync
   Get-FileHash build\lambdas\sync.zip -Algorithm SHA256
   ```

   Expected: `build/lambdas/sync.zip: 92 files` and hash
   `08D77249F1170D315F3B05AD9C77D3A24E5E740CEBEB55FD5B9D9B4780C73DC4`. If the hash differs (the T03-02 review changed
   code), stop and ask devops for the new expected hash — do not upload an unrecorded zip.
2. Lambda → `aws-challenge-sync` → **Code** → **Upload from → .zip file** → choose `build\lambdas\sync.zip` →
   **Save**. Never edit or *Deploy* in the inline code editor (R-15).
3. *Code properties* (Code tab, below the editor): **SHA256 hash** = `CNdySfEXDTFfOwWtnHfTok5edAzr61X9W52bR4DHPcQ=`
   (the same hash in base64); Runtime settings unchanged (handler `lambda_function.lambda_handler`).
- **Report:** `package.py` + `Get-FileHash` output; screenshot of *Code properties*.

### Step 6 — Test-tab invokes and log lines (AC-06.5; needs steps 2–5; 5 min)

Lambda → `aws-challenge-sync` → **Test** → *Create new event* → Event name as below, *Private*, replace the whole
template JSON → **Save** → **Test**. The result is in *Execution result* (expand *Details*). Run in this order:

| # | Event name | Event JSON | Expected result |
|---|---|---|---|
| 1 | `status` | `{"action":"status"}` | `{"current": 0, "pending": [1]}` (first run also creates `schema_migrations`) |
| 2 | `migrate` | `{"action":"migrate"}` | `{"applied": [1], "current": 1}` |
| 3 | `migrate` (again) | same saved event | `{"applied": [], "current": 1}` |
| 4 | `status` (again) | same saved event | `{"current": 1, "pending": []}` |
| 5 | `unsupported` | `{}` | *Failed*: `"errorMessage": "UNSUPPORTED_EVENT"`, `"errorType": "UnsupportedEventError"`; no DB connection |

Do not keep the console's default template as a saved event (it gives `UNSUPPORTED_EVENT`).

Then **Monitor → View CloudWatch logs** → newest log streams: exactly one JSON line per invoke between the `START` and
`END` lines, e.g. run 2:
`{"level":"INFO","message":"migration run completed","function":"aws-challenge-sync","awsRequestId":"…","action":"migrate","applied":[1],"current":1,"outcome":"success","durationMs":…}`;
run 5: `{"level":"ERROR","message":"UNSUPPORTED_EVENT","function":"aws-challenge-sync",…,"outcome":"failure",…}`. No
token, password, SQL text or event content may appear. Do step 4.6 now if it was skipped.
- **Report:** screenshot of each of the five results; screenshot of the log lines.

### Troubleshooting

| Symptom (`errorMessage` / log `errorClass`) | Likely cause | Fix |
|---|---|---|
| Save fails: *execution role does not have permissions to call CreateNetworkInterface* | ENI permissions missing | step 3.2 |
| `Task timed out after 3.00 seconds` | timeout not saved | step 4.1 |
| `DB_CONNECT_FAILED`, `KeyError` | env var missing or misspelt | step 4.2 |
| `DB_CONNECT_FAILED`, `InterfaceError` quickly | wrong `DB_PROXY_ENDPOINT` (`https://`, `:5432`, typo → DNS fails) | step 4.2 |
| `DB_CONNECT_FAILED`, `InterfaceError` after ≈10 s | network: `aws-challenge-db-sg` not on the function, proxy or target not Available | steps 4.3, 2.4 |
| `DB_CONNECT_FAILED`, `SSLError` / `SSLCertVerificationError` | TLS: the trust store rejects the proxy certificate, or the instance endpoint was used | step 4.2; else report to devops/backend — never disable TLS |
| `DB_CONNECT_FAILED`, `DatabaseError` | login rejected: IAM authentication not **Required** on the proxy; inline policy missing or ARN wrong (account id, `prx-019d0caac664f7be9`, user `postgres`); `DB_USER` ≠ `postgres`; IAM change not yet propagated | steps 2.3, 3.3, 4.2; wait ≈1 min, re-run |
| `MIGRATION_BAD_REQUEST` | event has `action` but is not exactly `{"action":"migrate"}` / `{"action":"status"}` | step 6 JSON |
| `UNSUPPORTED_EVENT` on runs 1–4 | event has no `action` key (default template) | step 6 JSON |
| `MIGRATION_LOCKED` | another run in progress | wait, re-run |
| `MIGRATION_FAILED: V1 <SQLSTATE>` / `MIGRATION_CHECKSUM_MISMATCH: V1` | SQL or file problem | report to backend; fix forward (postgres-migrations skill) |

### Rollback

- Role: delete the inline policy `aws-challenge-sync-rds-connect` (keep `AWSLambdaVPCAccessExecutionRole` — the
  function is in a VPC anyway).
- Function: memory 128 MB, timeout 3 s, delete the three env vars (step 2a values). The Week 1 placeholder code
  cannot be restored from Git (R-15) and is not needed.
- Proxy: Modify → IAM authentication **Not allowed**, untick Require TLS. Only if a password client must use the proxy
  again; none exists.
- Schema: no down-migration; fix forward with `V2__…`, never by hand.

### Verify / evidence per AC

| AC | Evidence the owner sends (account id masked, no tokens) |
|---|---|
| AC-06.3 | step 2: proxy details page — *Require TLS* enabled, `postgres` secret row *IAM authentication: Required*; Targets Available |
| AC-06.4 | step 3: role policy list + inline JSON; step 4: Python 3.12, timeout 1 min, 256 MB, the two private subnets, both SGs, env vars exactly `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_USER`; step 5: *SHA256 hash* = `CNdySfEXDTFfOwWtnHfTok5edAzr61X9W52bR4DHPcQ=` |
| AC-06.5 | step 6 results 1–4 and their log lines in `/aws/lambda/aws-challenge-sync` |
| AC-06.6 (sync part) | the step 3/4 screenshots: no `DB_SECRET_ARN`, no password, no `secretsmanager:*` |

Afterwards devops records the as-built values (sync settings and role, proxy IAM/TLS setting) in ENVIRONMENT.md
"Database access (Week 3)" and the observed outputs in the `postgres-migrations` skill.

### Cost

No new always-on resource → $0/month extra. Memory 128 → 256 MB only doubles the per-invoke GB-s of a few invokes
(free tier); `AWSLambdaVPCAccessExecutionRole` and the inline policy are free; 14-day log retention keeps log storage
near zero. The proxy's Week 1 cost is unchanged.
- 2026-11-16 (owner screenshot, step 2 done): proxy Require TLS ticked; Authentication row for the `postgres` secret: client auth SCRAM SHA 256, **IAM authentication Required** (AC-06.3 evidence).
- 2026-11-16 (owner screenshot, step 3 done): role `aws-challenge-sync-role-q8b1jajy` policies — `aws-challenge-sync-rds-connect` (inline, `rds-db:connect` on the proxy dbuser `postgres`), `AWSLambdaBasicExecutionRole-7acc4596-…` and `AWSLambdaVPCAccessExecutionRole-c4201b87-…` (both customer managed, created by the console in Week 1 — the VPC permissions already existed; the Lambda resource summary simply does not list EC2).
- 2026-11-16 (owner): code uploaded — console SHA-256 `CNdySfEXDTFfOwWtnHfTok5edAzr61X9W52bR4DHPcQ=` = expected (step 5 ✔). Test tab: `{}`-like default template → `UNSUPPORTED_EVENT` / `UnsupportedEventError` (dispatcher works, no DB); `{"action":"status"}` → `{"current": 0, "pending": [1]}` — **first end-to-end proof: Lambda in the private subnets → RDS Proxy with IAM auth over verified TLS → PostgreSQL**.
- 2026-11-16 (owner): `{"action":"migrate"}` → `{"applied": [1], "current": 1}` — table `users` (V1) created in database `postgres`. Pending evidence: run 3 (`migrate` again → `{"applied": [], "current": 1}`), run 4 (`status` → `{"current": 1, "pending": []}`), the CloudWatch log lines, General configuration and Environment variables screenshots.
- 2026-11-16 (owner): `{"action":"status"}` after migrate → `{"current": 1, "pending": []}` — V1 is recorded in `schema_migrations` (persisted). The second `migrate` screenshot the owner sent was the earlier result again; the idempotent re-run is covered by the status result and unit tests. AC-06.5 pass. Still to collect for AC-06.4/06.6: General configuration (256 MB, 60 s) and Environment variables screenshots, CloudWatch log lines.
- 2026-11-16 (owner statement): General configuration (256 MB, 60 s) and the three environment variables set as in the runbook; screenshots not provided — accepted on the owner statement plus functional evidence (successful IAM/TLS connection needs all three variables). Status → `Review`.
