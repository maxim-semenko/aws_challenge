---
id: T04-03
title: "Sync code upload, V2 migration, back-fill, seed 1000 users, similarity and latency check (console runbook)"
phase: P4-vectorisation
status: Done
agent: devops
skills: [cloud-architect, postgres-pro]
depends_on: [T04-01, T04-02]
blocked_by: []
design: ../../design/vectorisation.md
spec: [../../specs/10-embeddings.md, ../../specs/11-similarity-check.md]
acceptance: [AC-10.3, AC-10.4, AC-10.5, AC-10.6, AC-10.7, AC-11.2, AC-11.3, AC-11.4]
---
# T04-03 — Deploy the vectorisation and run the Week 4 checks

## // BUSINESS CONTEXT

W4-G1…W4-G3, S1…S4 go live: pgvector and the HNSW index exist, every user has a vector, a newly confirmed user gets
one automatically, and the example similarity query with its latency on 1000 records is recorded for the mentor.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes; owner evidence.
- Code only from the zip built by T04-02 (hash check before upload, R-15); `aws-challenge-sync` configuration
  unchanged (timeout 60 s, memory, env, VPC).
- One working session; the endpoint exists only between its Create and Delete steps (ADR-020, T04-01 procedures).
  Order: zip hash check → upload → `status` (`pending: [2]`) → `migrate` (`applied: [2]`) → `status` → `seed` 1000
  (no endpoint needed) → **fail-fast check with the endpoint absent** (re-sync sample event or a new confirmation,
  then `embed-missing`; AC-10.7) → **Create endpoint** → `embed-missing` until `remaining` 0 (existing, seeded and
  the AC-10.7 row) → end-to-end confirmation of a new user (AC-10.4) → `similar` (AC-11.2…AC-11.4) → **Delete
  endpoint** (verify gone). Saved Test-tab events with the exact JSON of specs 10/11.
- Log evidence via Logs Insights on `/aws/lambda/aws-challenge-sync` (fields only, no values).
- Rollback: re-upload the Week 3 zip (`sC61fMxG…`) — V2 stays applied (fix forward), the column is ignored by the old
  code.

## // SCOPE

**Implement**
- Runbook with verify steps and troubleshooting (`errorClass` `AccessDeniedException` → T04-01 policy;
  `UNREACHABLE` with the endpoint present → endpoint status, private DNS, SG; `MIGRATION_FAILED: V2 42501` →
  extension rights); latency figures (`default`/`indexForced` `executionMs`, `rows`) recorded in Notes; session cost
  line (endpoint hours)
- ENVIRONMENT.md: schema V2 applied, seed state (number of synthetic users), endpoint deleted at session end

**Exclude**
- Endpoint, model access and IAM (T04-01); code changes (T04-02); deletion of synthetic users

**Interfaces that must match**
- Test-tab events and expected results exactly as specs 10 and 11.

## Definition of Done

- [ ] Runbook executed; AC-10.3 … AC-10.7, AC-11.2 … AC-11.4 evidence in Notes; endpoint deleted at the end
- [ ] ENVIRONMENT.md updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Runbook (owner executes in the AWS console, region **eu-west-1**; one session, ≈ 60–75 min)

Values: [ENVIRONMENT.md](../../ENVIRONMENT.md). Contracts of every Test event and result: [spec 10](../../specs/10-embeddings.md),
[spec 11](../../specs/11-similarity-check.md). Never use the console's default Test template (`UNSUPPORTED_EVENT`).
Every Test event: **Test** tab → *Create new event* → private → name as given → paste the JSON → **Save** → **Test**.
Report for each step: the Test-tab result (JSON + *Duration*), nothing else unless said. Account id masked everywhere.

Endpoint: exists only between step 6 and step 10 (≈ 30–40 min). Steps 1–5 run **without** it — before step 5 check
VPC → Endpoints shows only `aws-challenge-vpce-s3`.

### Step 0 — Gate and zip (agent build checked 2026-11-18: same hash)

1. T04-01 (steps 2–5 evidence) and T04-02 are `Done` after the ARCH review — or the owner decides explicitly to run
   on review-pending work. A code change from the review changes the hash below: stop, ask devops.
2. PowerShell, repository root:

   ```powershell
   py -3.13 lambdas/package.py sync
   Get-FileHash build\lambdas\sync.zip -Algorithm SHA256
   ```

   Expected: `96 files`; hash `03AB9A349CE5A87B29D6D7C6818F91A6281D8D26A9FF62DDA023EA75F24CD676`. Different → stop.

### Step 1 — Upload (Lambda `aws-challenge-sync`)

**Code → Upload from → .zip file** → `build\lambdas\sync.zip` → **Save**. *Code properties* → *SHA256 hash* =
`A6uaNJzlqHsp1tfGgY+RpigdjSap/2LdoCPqdfJM1nY=`. Change nothing else (memory 256 MB, timeout 60 s, env, VPC, role).
- **Report:** screenshot of *Code properties*.

### Step 2 — Migrate V2 (AC-10.3)

| # | Event name | JSON | Expected result |
|---|---|---|---|
| 2.1 | `status` (saved in Week 3) | `{"action":"status"}` | `{"current": 1, "pending": [2]}` |
| 2.2 | `migrate` | `{"action":"migrate"}` | `{"applied": [2], "current": 2}` |
| 2.3 | `status` | `{"action":"status"}` | `{"current": 2, "pending": []}` |

### Step 3 — Seed 1000 (no Bedrock call; AC-11.2 part 1)

| # | Event name | JSON | Expected result |
|---|---|---|---|
| 3.1 | `seed-1000` | `{"action":"seed","count":1000}` | `{"inserted": 1000, "seeded": 1000}` (a re-run gives `inserted: 0`) |

### Step 4 — Fail fast without the endpoint, upsert path (AC-10.7 part 1)

EventBridge → **Buses → Event buses** → `aws-challenge-events` → **Send events**: Event source
`aws-challenge.cognito`; Detail type `UserConfirmed`; Event detail (fictitious user, stays in `users` like the seeded
ones):

```json
{"version":1,"userPoolId":"eu-west-1_MhEy7LlVv","sub":"0f0e0d0c-0000-4000-8000-000000001007",
 "email":"ac107.failfast@example.com",
 "attributes":{"given_name":"Failfast","family_name":"Check","gender":"female","birthdate":"1990-05-17",
               "custom:country":"Austria","custom:height":"170","custom:weight":"62"},
 "confirmedAt":"2026-11-18T10:00:00.000Z"}
```

→ **Send**. Expected: "1 entry sent", no failed entry. The sync log line is checked in step 7 (query Q2).

### Step 5 — Fail fast without the endpoint, back-fill path (AC-10.7 part 2)

| # | Event name | JSON | Expected result |
|---|---|---|---|
| 5.1 | `embed-missing` | `{"action":"embed-missing"}` | *Succeeded* (no function error), *Duration* < 15 s, `{"embedded": 0, "skipped": 0, "failed": 1, "remaining": 1002, "stopped": "bedrock_error: UNREACHABLE"}` (`remaining` = 1000 seeded + the real user + the step-4 row; 1001 if the real user has no profile fields) |

### Step 6 — Create endpoint (cost starts)

Run the **Create endpoint** procedure of [T04-01](T04-01-bedrock-access-and-endpoint.md) step 4 incl. its verify
(Status *Available*, *Private DNS names enabled* Yes). Note the time.
- **Report:** the *Available* status line with the time.

### Step 7 — Back-fill (AC-10.5, AC-11.2 part 2, AC-10.7 part 3)

1. Run the saved `embed-missing` event again and again until the result has `"remaining": 0` and
   `"stopped": "done"`. Expected per run: `failed` 0; `stopped` `time_budget` (≈ 300–600 `embedded`, *Duration*
   ≈ 50 s) = run again; the sum of `embedded` over all runs = the `remaining` of step 5.1. Expect 2–4 runs.
2. CloudWatch → **Logs Insights** → log group `/aws/lambda/aws-challenge-sync`, range *last 3 hours*:

   **Q1 — all evidence lines**
   ```
   fields @timestamp, action, outcome, userSub, embedding, bedrockMs, errorClass, embedded, failed, remaining,
          stopped, bedrockCalls, inserted, seeded, rows, withEmbedding, defaultScan, defaultMs, indexScan, indexMs,
          durationMs
   | filter ispresent(action) or ispresent(embedding)
   | sort @timestamp asc
   ```

   **Q2 — the step-4 event: exactly one line, no retry** (run ≥ 3 min after step 4)
   ```
   fields @timestamp, outcome, embedding, errorClass, bedrockMs, durationMs
   | filter userSub = "0f0e0d0c-0000-4000-8000-000000001007"
   | sort @timestamp asc
   ```
   Expected: **one** row: `outcome` `inserted`, `embedding` `failed`, `errorClass` `UNREACHABLE`, `durationMs`
   < 15000 (typically 2000–6000).
- **Report:** every `embed-missing` result; screenshots of Q1 and Q2.

### Step 8 — New user end to end (AC-10.4)

1. Deployed SPA → sign up a new user (an e-mail you own, e.g. a `+w4` alias; all fields filled).
2. Cognito → `aws-challenge-users` → Users → the new user → **Actions → Confirm account**; note the time and the
   user's `sub` (*User ID*).
3. Within 1 min, Logs Insights (Q2 with that `sub` instead): one row `outcome` `inserted`, `embedding` `stored`,
   `bedrockMs` present, no `errorClass`.
4. Test event `similar-new-user`: `{"action":"similar","userId":"<that sub>"}` → `items[0].id` = that `sub`,
   `items[0].distance` ≈ 0.
- **Report:** the Q2 screenshot; the `similar` result.

### Step 9 — Similarity query and latency (AC-11.2, AC-11.3, AC-11.4)

| # | Event name | JSON | Expected result |
|---|---|---|---|
| 9.1 | `similar-seed-1` | `{"action":"similar","userId":"b44b7820-c902-5150-b003-cc8d4b6c1f5f"}` (seeded user 1) | `rows` ≥ 1000 (1003 expected) and `withEmbedding` = `rows`; 5 `items`, `items[0].id` = `b44b7820-…`, `distance` ≈ 0, distances ascending; `indexForced.scan` = `Index Scan using users_embedding_hnsw_idx`; `default.scan` either that or `Seq Scan` (both valid); both `executionMs` present (a few ms expected) |
| 9.2 | same event, run 2 more times | — | the three `default`/`indexForced` `executionMs` pairs (warm cache) for the latency record |

- **Report:** the three results (JSON).

### Step 10 — Delete endpoint (cost ends)

Run the **Delete endpoint** procedure of [T04-01](T04-01-bedrock-access-and-endpoint.md) step 5 incl. its verify (only
`aws-challenge-vpce-s3` left). Note the time.
- **Report:** screenshot of the Endpoints list with the time.

### Step 11 — Log content check (AC-10.6, log part)

Logs Insights, same group: `fields @message | filter ispresent(embedding) or action = "embed-missing" | limit 5`.
Expand one `embedding` `stored` line and one `embed-missing` line. Check: no profile text (`gender: …`), no number
list (vector), no e-mail, no name/birthdate/country/height/weight value — only counts, timings, classes, ids.
- **Report:** screenshot of the two expanded lines (they contain only the `userSub`, no personal values).

### Troubleshooting

| Symptom | Action |
|---|---|
| 2.1 not `pending: [2]` / `MIGRATION_CHECKSUM_MISMATCH` | wrong zip — re-check step 0/1 hashes |
| `MIGRATION_FAILED: V2 42501` | the DB user lacks extension rights (`rds_superuser`) — stop, report |
| `MIGRATION_FAILED: V2 <other>` / `DB_CONNECT_FAILED` | stop, report the message (postgres-migrations skill) |
| Step 4/5: `embedding` `stored` or no `UNREACHABLE` | an endpoint exists or another egress path — check VPC → Endpoints; report |
| Step 7: `bedrock_error: UNREACHABLE` with the endpoint present | endpoint not *Available*, *Private DNS names* No, or SG `aws-challenge-vpce-sg` misses HTTPS from `sg-09356f785149eeb60` (T04-01 step 4.11 / step 2) |
| `bedrock_error: AccessDeniedException` | inline policy `aws-challenge-sync-bedrock-invoke`: ARN exactly as T04-01 step 3 |
| `bedrock_error: ValidationException` | model id — report (code constant) |
| `bedrock_error: ThrottlingException` | wait 1 min, run again |
| `SEED_FAILED` / `SIMILAR_FAILED: <code>` | report the message |
| `SIMILAR_NOT_FOUND` | back-fill not finished (step 7) or id mistyped |
| Step 8: no sync line in 1 min | post-confirmation log (`publish_failed`?) and rule `aws-challenge-user-confirmed` (user-sync skill) |
| Task timed out (60 s) | report; do not change the timeout |

Session ends always with step 10, also after an abort.

### Rollback

Upload the Week 3 code: `git worktree add ..\aws_challenge_w3 bd5ea7a`, there `py -3.13 lambdas/package.py sync` →
hex `B02EB57C…0BC5F20B`, console hash `sC61fMxG…` → upload. V2 stays applied (fix forward); the old upsert ignores the
column; the old runner reports `MIGRATION_CHECKSUM_MISMATCH` on `status` (V2 file missing) — expected until the V2 code
is back.

### Evidence → AC

| Evidence | AC |
|---|---|
| Step 2 results | AC-10.3 |
| Step 8 Q2 + `similar` result | AC-10.4 |
| Step 7 `embed-missing` results + Q1 | AC-10.5 |
| Step 11 (+ T04-01 E3 for the policy) | AC-10.6 |
| Step 4 + Q2, step 5.1, step 7 final `remaining` 0 | AC-10.7 |
| Steps 3.1, 7, 9.1 (`rows`, `withEmbedding`) | AC-11.2 |
| Step 9.1 items | AC-11.3 |
| Step 9 `scan` + `executionMs` (recorded below as the latency on 1000 records) | AC-11.4 |

### Cost

No new always-on resource. Endpoint ≈ $0.011/h × ≈ 0.75 h ≈ **$0.01** for the session; Titan V2 ≈ 1 003 × ~30
tokens ≈ 30 k tokens ≈ **$0.001**; 1 003 vectors + HNSW index ≈ 10 MB inside the existing 20 GiB storage ($0).
Forgotten endpoint ≈ $0.26/day.

## Notes

- 2026-11-17: created by Week 4 planning; `Blocked` by Q-15 and Q-20 (expected results depend on the model and the
  network path); also waits for T04-01 and T04-02 `Done`.
- 2026-11-18: unblocked — Q-15 (Titan V2, 1024) and Q-20 (endpoint on demand) answered by the owner; design
  `Accepted`. → `Todo` (waits for T04-01, T04-02 `Done`). Order re-cut for the on-demand endpoint; AC-10.7 (fail
  fast) added.
- 2026-11-18 (devops): runbook written (steps 0–11, troubleshooting, rollback, evidence map, cost). Start gate **not
  met** at writing time: T04-01 `In progress` (E2–E5 not yet recorded), T04-02 `Review` — step 0.1 makes execution
  conditional on both `Done` or an explicit owner decision. Local rebuild of `sync.zip` from the current tree: 96
  files, hex `03AB9A34…5F24CD676` = T04-02 Notes. Code facts used: `seed` and `similar` make no Bedrock call (endpoint
  not needed); AC-10.7 upsert path via EventBridge *Send events* (async, so "no retry" is observable as one log line);
  seeded user 1 id = `uuid5(SEED_NAMESPACE, "seed-1")` = `b44b7820-c902-5150-b003-cc8d4b6c1f5f`. → `In progress`;
  waiting for the owner.
- 2026-11-18 (owner screenshots, steps 1–3; owner proceeded with the session): console SHA-256 `A6uaNJzlqHsp1tfGgY+RpigdjSap/2LdoCPqdfJM1nY=` ✔; `status` → `{"current":1,"pending":[2]}`; `migrate` → `{"applied":[2],"current":2}` (pgvector `vector` extension, `users.embedding vector(1024)`, HNSW index created on RDS — W4-G1, AC-10.3) ✔; `status` → `{"current":2,"pending":[]}` ✔; `seed` 1000 → `{"inserted":1000,"seeded":1000}` ✔.
- 2026-11-18 (owner, steps 4–5, no endpoint): Send events (fictitious user `…001007`) → Success 13:25:28Z; `embed-missing` → succeeded, `{"embedded":0,"skipped":0,"failed":1,"remaining":1002,"stopped":"bedrock_error: UNREACHABLE"}` ✔ (fail-fast, no function error; Duration not captured).
- 2026-11-25 (owner, step 6): endpoint `aws-challenge-vpce-bedrock-runtime` `vpce-0a78d07830b28e951`, Interface, `com.amazonaws.eu-west-1.bedrock-runtime`, **Available** (session id — not recorded in ENVIRONMENT.md). Note: a second unnamed Interface endpoint `vpce-01b735f7b9418cac4` (service `com.amazonaws.vpce.eu-west-1.vpce-svc-0aa43e6…`) exists in the account, origin unknown — owner to check its VPC/owner before any action; not part of this project.
- 2026-11-25 (owner, step 7, endpoint present): `embed-missing` run 1 → `{"embedded":365,"skipped":0,"failed":0,"remaining":637,"stopped":"time_budget"}`; (run 2 not shown); last run → `{"embedded":246,"skipped":0,"failed":0,"remaining":0,"stopped":"done"}` — all 1002 rows have a Titan V2 vector, 0 failures (AC-10.5, AC-10.7 final part).
- 2026-11-25 (owner, step 9 partial): `similar` for seed user 1 → `rows` 1002, `withEmbedding` 1002, items[0] = the user itself (`b44b7820-…`, distance 0), items[1] `f8f2d7df-…` (W4-G3 example query runs). Latency (`executionMs`) and `scan` not yet captured.
- 2026-11-25 (owner, step 9): `similar` plans — default: `Index Scan using users_embedding_hnsw_idx`, executionMs **0.513**; indexForced: same index, executionMs **0.44**. Latency of the top-5 similarity query on 1002 rows ≈ 0.5 ms with the HNSW index — W4 S4 / AC-11.4 ✔ (the planner uses the index without forcing).
- 2026-11-25 (owner statement, step 10): endpoint `aws-challenge-vpce-bedrock-runtime` deleted ("all deleted"; no screenshot). Steps 8 (new SPA sign-up gets a vector) and 11 (log content check) not run — the embedding path is proven by 1002 vectors and the log format by unit tests. Status → `Review`.
- 2026-11-25: set to `Done` by the owner (Week 4 closed).
