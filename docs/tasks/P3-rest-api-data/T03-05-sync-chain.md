---
id: T03-05
title: "Sync chain: EventBridge bus and rule, trigger function, Cognito trigger, Sync Lambda code upload (console runbook)"
phase: P3-rest-api-data
status: Done
agent: devops
skills: [cloud-architect, cognito-user-pool]
depends_on: [T03-03, T03-04]
blocked_by: []
design: ../../design/user-sync.md
spec: ../../specs/07-user-sync.md
acceptance: [AC-07.3, AC-07.4, AC-07.5, AC-07.6]
---
# T03-05 — Sync chain on AWS (console runbook)

## // BUSINESS CONTEXT

W3-G1, S2: the curriculum's chain Cognito → EventBridge → Lambda goes live; from then on every confirmed user is
copied to PostgreSQL, and existing users are back-filled.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes; owner evidence (account id masked, log
  screenshots without personal values).
- Settings exactly as design user-sync §3: bus `aws-challenge-events` (no archive), rule
  `aws-challenge-user-confirmed` (pattern, target, retry 1 h / 5), function `aws-challenge-post-confirmation` (Python
  3.12, **no VPC**, 256 MB, 5 s, env `EVENT_BUS_NAME`, role `events:PutEvents` on the bus ARN only), PostConfirmation
  trigger on the pool. Log retention 14 days; tags per CLAUDE.md §7.
- `aws-challenge-sync`: **code upload only** (zip from T03-04); its configuration, env vars and role were set by
  T03-03. After the upload the Test-tab event `{"action":"status"}` must still return `{"current":1,"pending":[]}`
  (proves the migration files are byte-identical and the runner still reachable).
- Code only from the zips built by T03-04 (R-15). Trigger changes take up to 70 s to apply (AWS docs).
- As-built values are taken from ENVIRONMENT.md (T03-03); if any is missing there, the runbook's first step asks the
  owner to read and report it.

## // SCOPE

**Implement**
- Runbook in the order: bus → trigger function + role → Cognito trigger → sync code upload + `status` check → rule; verify steps for
  AC-07.3 … AC-07.6 (new test user via the deployed SPA, confirm, check logs and the row)
- Re-sync / back-fill runbook (EventBridge *Send events*) and its run for every user confirmed before the trigger
  existed (AC-07.5)
- ENVIRONMENT.md: new "Sync chain (Week 3)" section; skills `user-sync` (as-built) and `cognito-user-pool` (trigger)
  updated

**Exclude**
- DLQ / on-failure destination (design: not in Week 3); attribute-change sync (R-12)

**Interfaces that must match**
- Names, event source/detail-type and env vars as spec 07 and design user-sync.

## Definition of Done

- [ ] Runbook executed; AC-07.3 … AC-07.6 evidence in Notes; trigger cold-start duration recorded (R-02)
- [ ] ENVIRONMENT.md and skills updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-17 and Q-18. AC-07.4's last step (row visible in the admin
  table) needs T03-07/T03-08; until then the row is shown by the sync log `inserted` and checked again in T03-10.
- 2026-11-13: Q-17 A and Q-18 A accepted by the owner (ADR-016, ADR-006 revised); design user-sync `Accepted` →
  `Todo` (waits for T03-03, T03-04 `Done`).
- 2026-11-16 (ARCH, owner decisions): `sync` configuration (timeout 60 s, env, role) moved to T03-03, which also runs
  the first migration through `sync`; this task only uploads the upsert version of the code. AC-06.6 (sync part) moved
  to T03-03; spec 06 dropped from this task. Runtime Python 3.12 for both functions (ADR-015 revised).
- 2026-11-16 (devops): status → `In progress`; runbook below written. **Start gate not fully met:** T03-03 and
  T03-04 are `Review`, not `Done` (design `Accepted`, not blocked) — step 0 asks the owner to decide. Order changed
  against SCOPE on purpose: sync code and rule go live **before** the Cognito trigger, so the first real
  `UserConfirmed` event already finds the whole chain (no event lost to a missing rule, none sent to the old sync
  code). Trigger role created by hand (not "basic Lambda permissions"), because the console's generated logs policy
  has `logs:CreateLogGroup` on `arn:aws:logs:…:*`; the log group is pre-created with 14-day retention instead.

## Runbook (owner executes in the AWS console, region **eu-west-1 / Europe (Ireland)**)

| Placeholder | Value (homes: ENVIRONMENT.md, T03-04 Notes) |
|---|---|
| Pool | `aws-challenge-users` (`eu-west-1_MhEy7LlVv`) |
| Bus ARN | `arn:aws:events:eu-west-1:<ACCOUNT_ID>:event-bus/aws-challenge-events` |
| `post-confirmation.zip` | 2 files; SHA-256 hex `0BDCBA9F97F61B0C9C61AB00A2BC8EFEAADBB797343A0D5450E5373B434F60F4`; console *SHA256 hash* `C9y6n5f2GwycYasAoryO/qrbt5c0Og1UUOU3O0NPYPQ=` |
| `sync.zip` | 93 files; SHA-256 hex `B02EB57CCC46173D0A81C18D8AEEBD356B62E8A07A2D90A0094921490BC5F20B`; console *SHA256 hash* `sC61fMxGFz0KgcGNiu69NWti6KB6LZCgCUkhSQvF8gs=` |
| Tags (every new resource) | `project` = `aws-challenge`, `env` = `dev`, `owner` = `max` |
| `<ACCOUNT_ID>` | 12 digits, console top-right menu → Account ID. Paste **only** into the IAM JSON editor; mask it in every screenshot; never into the repo or chat |

Do not confirm any user in Cognito between step 4 and step 6 (an event would hit an unfinished chain); if it happens,
back-fill that user in step 8.

### Step 0 — Gate and zips (5 min)

1. T03-03 and T03-04 are `Review`. Either set them `Done` after the ARCH review, or decide explicitly to deploy the
   review-pending code. If the review changes code, the hashes above change — stop and ask devops.
2. PowerShell, repository root, on the reviewed working tree:

   ```powershell
   py -3.13 lambdas/package.py post-confirmation
   py -3.13 lambdas/package.py sync
   Get-FileHash build\lambdas\post-confirmation.zip, build\lambdas\sync.zip -Algorithm SHA256
   ```

   Expected: `2 files` / `93 files` and the two hex hashes above. Any difference → stop, do not upload.
- **Report:** the console output.

### Step 1 — EventBridge bus `aws-challenge-events` (3 min)

1. EventBridge → **Buses → Event buses** → **Create event bus**.
2. Name `aws-challenge-events`; Description `Week 3 user sync (UserConfirmed)`; Encryption: **AWS owned key**
   (default); Archive: **Disabled**; Schema discovery: **Disabled**; Resource-based policy: empty; Logs (if offered):
   **off**; Tags: the three tags → **Create**.
- **Report:** screenshot of the bus details (name, ARN with account id masked, no archive).

### Step 2 — Log group and role for the trigger (IAM, CloudWatch; 7 min)

1. CloudWatch → **Log groups** → **Create log group**: name `/aws/lambda/aws-challenge-post-confirmation`; retention
   **2 weeks (14 days)**; log class **Standard**; KMS key empty; the three tags → **Create**.
2. IAM → **Roles** → **Create role** → Trusted entity **AWS service**, use case **Lambda** → **Next** → attach **no**
   policy → **Next** → Role name `aws-challenge-post-confirmation-role`, description `Trigger: PutEvents to
   aws-challenge-events + own logs`, the three tags → **Create role**.
3. Open the role → **Add permissions → Create inline policy** → **JSON** → replace everything with:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "PutUserConfirmedEvents",
         "Effect": "Allow",
         "Action": "events:PutEvents",
         "Resource": "arn:aws:events:eu-west-1:<ACCOUNT_ID>:event-bus/aws-challenge-events"
       },
       {
         "Sid": "WriteOwnLogs",
         "Effect": "Allow",
         "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
         "Resource": "arn:aws:logs:eu-west-1:<ACCOUNT_ID>:log-group:/aws/lambda/aws-challenge-post-confirmation:*"
       }
     ]
   }
   ```

   **Next** → policy name `aws-challenge-post-confirmation-policy` → **Create policy**. The role has exactly this one
   policy.
- **Report:** log group row (retention 2 weeks); role Permissions tab; inline policy JSON (account id masked).

### Step 3 — Function `aws-challenge-post-confirmation` (Lambda; 10 min)

1. Lambda → **Create function** → *Author from scratch*: name `aws-challenge-post-confirmation`; Runtime **Python
   3.12**; Architecture **x86_64**; *Change default execution role* → **Use an existing role** →
   `aws-challenge-post-confirmation-role`; *Additional configurations*: **Enable VPC unticked**, function URL off,
   code signing off, tags if offered → **Create function**.
2. **Configuration → General configuration → Edit**: Memory **256** MB; Ephemeral storage **512** MB; Timeout **0** min
   **5** sec; SnapStart None → **Save**.
3. **Configuration → Environment variables → Edit**: one variable `EVENT_BUS_NAME` = `aws-challenge-events` → **Save**.
4. **Configuration → VPC**: must show *No VPC configuration*. **Configuration → Tags**: the three tags.
   **Monitoring and operations tools → Logging configuration**: log group `/aws/lambda/aws-challenge-post-confirmation`
   (the one from step 2.1).
5. **Code → Upload from → .zip file** → `build\lambdas\post-confirmation.zip` → **Save**. *Code properties* →
   *SHA256 hash* = `C9y6n5f2GwycYasAoryO/qrbt5c0Og1UUOU3O0NPYPQ=`. *Runtime settings*: handler
   `lambda_function.lambda_handler`. Never edit or *Deploy* in the inline editor (R-15).
6. Smoke test (no rule exists yet, so the event goes nowhere): **Test** → new event `smoke-confirm-signup`, private,
   JSON (fictitious values):

   ```json
   {"version":"1","triggerSource":"PostConfirmation_ConfirmSignUp","region":"eu-west-1",
    "userPoolId":"eu-west-1_MhEy7LlVv","userName":"smoke-test",
    "callerContext":{"awsSdkVersion":"test","clientId":"test"},
    "request":{"userAttributes":{"sub":"00000000-0000-4000-8000-000000000000","email":"smoke.test@example.com"}},
    "response":{}}
   ```

   Expected: *Succeeded*, the response is the same JSON; log line with `"outcome":"published"`. `publish_failed` →
   troubleshooting.
- **Report:** screenshots of General configuration, Environment variables, VPC, Code properties, the test result and
  its log line.

### Step 4 — Upload the new `sync` code (configuration unchanged; 5 min)

1. Lambda → `aws-challenge-sync` → **Code → Upload from → .zip file** → `build\lambdas\sync.zip` → **Save**.
   *SHA256 hash* = `sC61fMxGFz0KgcGNiu69NWti6KB6LZCgCUkhSQvF8gs=`. Do not change memory, timeout, env, VPC or role.
2. **Test** → saved event `status` (`{"action":"status"}`) → expected `{"current": 1, "pending": []}`.
3. **Test** → new event `userconfirmed-rejected` (proves the new route without writing a row):

   ```json
   {"id":"manual-test","source":"aws-challenge.cognito","detail-type":"UserConfirmed",
    "detail":{"version":1,"userPoolId":"eu-west-1_MhEy7LlVv","sub":"not-a-uuid","email":"x@example.com",
              "attributes":{},"confirmedAt":"2026-11-16T10:00:00.000Z"}}
   ```

   Expected: `{"outcome": "rejected"}`; log line `outcome` `rejected`, `invalidFields` `["sub"]`. Never test with a
   valid UUID here (that writes a row).
- **Report:** Code properties; the two results.

### Step 5 — Rule `aws-challenge-user-confirmed` (EventBridge; 5 min)

1. EventBridge → **Buses → Rules** → Event bus drop-down **`aws-challenge-events`** → **Create rule**.
2. Name `aws-challenge-user-confirmed`; Description `UserConfirmed -> aws-challenge-sync`; Event bus
   `aws-challenge-events`; *Enable the rule on the selected event bus* on; Rule type **Rule with an event pattern** →
   **Next**.
3. Event source **Other**; skip the sample event; Creation method **Custom pattern (JSON editor)**:

   ```json
   {"source":["aws-challenge.cognito"],"detail-type":["UserConfirmed"]}
   ```

   → **Next**.
4. Target: **AWS service** → **Lambda function** → `aws-challenge-sync` (no version/alias). *Additional settings*:
   target input **Matched events**; *Maximum age of event* **1** h **0** min; *Retry attempts* **5**; Dead-letter
   queue **None**; leave any execution-role option off (Lambda targets use the function's resource policy) → **Next**
   → tags → **Next** → **Create rule**.
5. Verify the permission the console added: Lambda → `aws-challenge-sync` → **Configuration → Permissions** →
   *Resource-based policy statements*: principal `events.amazonaws.com`, action `lambda:InvokeFunction`, condition
   `AWS:SourceArn` = `arn:aws:events:eu-west-1:<ACCOUNT_ID>:rule/aws-challenge-events/aws-challenge-user-confirmed`.
   **Configuration → Asynchronous invocation**: retry attempts 2, max age 6 h (defaults, unchanged).
- **Report:** rule details (pattern, state *Enabled*), Targets tab (retry 1 h / 5, no DLQ), the sync resource-policy
  statement (account id masked).

### Step 6 — Cognito PostConfirmation trigger (3 min + up to 70 s to apply)

1. Cognito → User pools → `aws-challenge-users` → **Extensions** (left menu; older console: *User pool properties*)
   → **Lambda triggers → Add Lambda trigger**.
2. Trigger type **Sign-up** → **Post confirmation trigger**; Lambda function `aws-challenge-post-confirmation` →
   **Add Lambda trigger**.
3. Verify the invoke permission: Lambda → `aws-challenge-post-confirmation` → **Configuration → Permissions** →
   *Resource-based policy statements*: principal `cognito-idp.amazonaws.com`, action `lambda:InvokeFunction`,
   condition `AWS:SourceArn` = `arn:aws:cognito-idp:eu-west-1:<ACCOUNT_ID>:userpool/eu-west-1_MhEy7LlVv`. Missing →
   remove and re-add the trigger in the console (never add a statement without `SourceArn`).
4. Wait 70 s before step 7.
- **Report:** Extensions page (one trigger: Post confirmation → `aws-challenge-post-confirmation`); the resource-policy
  statement (account id masked).

### Step 7 — End-to-end test (AC-07.4, AC-07.6; 5 min)

1. Deployed SPA (`https://main.d67fa9mmezz1k.amplifyapp.com`) → sign up a **new** user with all eight fields.
2. Cognito → `aws-challenge-users` → Users → that user → **Actions → Confirm account** (cognito-user-pool skill).
   Status *Confirmed*. Note the time.
3. CloudWatch → **Logs Insights** → select both `/aws/lambda/aws-challenge-post-confirmation` and
   `/aws/lambda/aws-challenge-sync` → last 15 min →

   ```
   fields @timestamp, @log, outcome, userSub, durationMs, invalidFields, errorClass
   | filter ispresent(outcome)
   | sort @timestamp desc
   | limit 20
   ```

   Expected within 1 minute of the confirmation: post-confirmation `published` and sync `inserted`, **same
   `userSub`**, empty `invalidFields`.
4. Cold start (R-02): same page, only the post-confirmation log group:
   `fields @timestamp, @initDuration, @duration | filter @type = "REPORT" | sort @timestamp desc | limit 5` →
   record `@initDuration` + `@duration` of that invoke (must be far below 5000 ms).
5. AC-07.6: open both raw log lines (Log groups → newest stream): no e-mail, name, gender, birth date, country, height
   or weight value.
6. The row in the admin table (last part of AC-07.4) is checked in T03-10 once T03-07/T03-08 are live.
- **Report:** the two Insights results and both raw log lines (screenshots).

### Step 8 — Back-fill users confirmed before step 6 (AC-07.5; ~3 min per user)

1. Cognito → Users: list every user with *Confirmation status* **Confirmed** created before step 6 (expected
   `test@gmail.com`, `test1@gmail.com`, maybe more). An **unconfirmed** user (e.g. `test3@…`) needs no back-fill:
   *Confirm account* now fires the trigger.
2. Per user: user page → *User attributes* → copy `sub`, `email` and the attributes that are set.
3. EventBridge → **Buses → Event buses** → **Send events**: Event bus `aws-challenge-events`; Event source
   `aws-challenge.cognito`; Detail type `UserConfirmed`; Resources empty; Event detail:

   ```json
   {
     "version": 1,
     "userPoolId": "eu-west-1_MhEy7LlVv",
     "sub": "<sub>",
     "email": "<email>",
     "attributes": {
       "given_name": "<given_name>",
       "family_name": "<family_name>",
       "gender": "<gender>",
       "birthdate": "<YYYY-MM-DD as in Cognito>",
       "custom:country": "<country>",
       "custom:height": "<height>",
       "custom:weight": "<weight>"
     },
     "confirmedAt": "<now, UTC, e.g. 2026-11-16T15:00:00.000Z>"
   }
   ```

   Values as strings exactly as Cognito shows them; leave out an attribute that is not set (no empty strings,
   never `email_verified`). `confirmedAt` = time of the back-fill (the real confirmation time is not
   recorded by Cognito). → **Send**. Do not keep this JSON anywhere after sending (personal data).
4. Logs Insights (query of step 7.3, sync log group): one line with that `userSub` and `inserted`.
5. AC-07.5: for **one** of these users press **Send** again with the same detail → `updated`, same `userSub` (the
   upsert key is the `sub`, so still one row).
- **Report:** Insights result per user (`inserted`) and the second send (`updated`); the *Send events* screenshot only
  with the detail hidden or masked.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| post-confirmation `publish_failed`, `errorClass` `AccessDeniedException` | policy ARN wrong (account id, region, bus name) | step 2.3 |
| `publish_failed`, `KeyError` | `EVENT_BUS_NAME` missing/misspelt | step 3.3 |
| `publish_failed`, `ResourceNotFoundException` / `EndpointConnectionError` | bus name wrong; function accidentally in a VPC | steps 1, 3.4 |
| `published` but no sync line | rule on the default bus, pattern typo, rule disabled, target missing | step 5 |
| sync `UNSUPPORTED_EVENT` for the event | old sync code | step 4 |
| sync `rejected`, `invalidFields` `["sub"]` / `["email"]` | back-fill value mistyped | step 8.2–8.3, send again |
| sync `failure` / `DB_CONNECT_FAILED` | proxy / DB / IAM auth (T03-03 troubleshooting table) | fix, then re-send (step 8) |
| no post-confirmation log at all after *Confirm account* | trigger not saved or < 70 s; Cognito permission missing | step 6 |
| *Confirm account* shows an error | trigger timed out (> 5 s) or permission error | send the user's error text to devops; remove the trigger (rollback) |

### Rollback (reverse order, any step)

1. Cognito → Extensions → remove the Post confirmation trigger (confirmations work again exactly as before).
2. EventBridge → rule `aws-challenge-user-confirmed` → **Disable** (or delete; its Lambda permission statement on
   `sync` is removed with *Delete* only — remove it by hand otherwise).
3. Delete function `aws-challenge-post-confirmation`, role `aws-challenge-post-confirmation-role`, log group, bus.
4. `sync` code: leave the new zip (it still runs `status`/`migrate` unchanged); rows already written stay (no
   down-migration; fix forward).

### Verify / evidence per AC

| AC | Evidence (account id masked, no personal values) |
|---|---|
| AC-07.3 | steps 1, 2, 3 (no VPC, role with the one inline policy), 5 (pattern, target, retry 1 h / 5), 6; sync role without Secrets Manager: T03-03 step 3 evidence |
| AC-07.4 | step 7.3 (`published` + `inserted`, same `userSub`, within 1 min), 7.4 cold-start duration; admin-table row → T03-10 |
| AC-07.5 | step 8.4–8.5 (`inserted`, then `updated`) |
| AC-07.6 | step 7.5 raw log lines |

Afterwards devops records the as-built values in ENVIRONMENT.md "Sync chain (Week 3)" and updates the skills
`user-sync` and `cognito-user-pool` (trigger now exists).

### Cost

No always-on resource → **$0/month** extra. Custom bus: no charge for the bus; custom events $1.00 per million
(a few dozen here); rule matching and Lambda invocation by EventBridge free; Lambda 256 MB × < 1 s per confirmation
and CloudWatch Logs (14-day retention) within the free tier.
- 2026-11-17 (owner screenshots, steps 1–4): bus `aws-challenge-events` created (AWS owned key, retention 1 day default); role `aws-challenge-post-confirmation-role` created; function `aws-challenge-post-confirmation` smoke test Succeeded, response = the input event, code SHA-256 `C9y6n5f2GwycYasAoryO/qrbt5c0Og1UUOU3O0NPYPQ=` ✔; `aws-challenge-sync` new code SHA-256 `sC61fMxGFz0KgcGNiu69NWti6KB6LZCgCUkhSQvF8gs=` ✔, `userconfirmed-rejected` test → `{"outcome": "rejected"}` ✔ (new route works without writing a row).
- 2026-11-17 (owner): the first bus was created as the new EventBridge bus type "Custom" (ARN `event-busv2/aws-challenge-events/<id>`, subscriptions instead of rules) — incompatible with the runbook (rules) and the trigger policy ARN. Owner recreated `aws-challenge-events` as a Classic bus: ARN `arn:aws:events:eu-west-1:<ACCOUNT_ID>:event-bus/aws-challenge-events`, Rules tab available (created 2026-11-17 14:58 GMT+4). Runbook note: in the current console, choose the Classic bus type in step 1.
- 2026-11-17 (owner screenshots, steps 5–7): rule `aws-challenge-user-confirmed` on `aws-challenge-events` (pattern `{"source":["aws-challenge.cognito"],"detail-type":["UserConfirmed"]}`, target `aws-challenge-sync`, max age 1 h, 5 retries, no DLQ; created with the Advanced builder; no tags — owner skipped them); Cognito Post confirmation trigger → `aws-challenge-post-confirmation`. End-to-end (AC-07.4): new user signed up and confirmed in the console; Logs Insights over both groups — post-confirmation `published` 2026-11-17T11:09:50.905Z and sync `inserted` 2026-11-17T11:09:54.262Z, same `userSub` `12a5c484-…-ff1282cf8590` (~3.4 s end to end). The console `Confirm account` (AdminConfirmSignUp) fires the PostConfirmation trigger — confirmed. Remaining: back-fill of users confirmed before the trigger (step 8, AC-07.5), cold-start figure (R-02), raw log lines for AC-07.6.
- 2026-11-17 (owner decision): step 8 back-fill **waived** — AC-07.5 waived by the owner (users confirmed before the trigger stay out of `users`; admin rights come from the token group, not the table; more test users will be signed up through the SPA, Week 4 seeds its 1000 rows by script). Cold-start figure (R-02) and raw log lines (AC-07.6) not collected; the observed end-to-end latency (~3.4 s incl. EventBridge) shows the trigger stayed inside the 5 s Cognito limit. Status → `Review`.
- 2026-11-17: set to `Done` by the owner (Week 3 closed).
