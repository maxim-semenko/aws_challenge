# Spec 10 — Embeddings: pgvector column, Bedrock vectors on insert/update, back-fill

Requirements: [week-04](../requirements/week-04-vectorisation.md) W4-G1, W4-G2, S1, S2, S3 ·
Design: [vectorisation](../design/vectorisation.md) §1–§4, §5 (`embed-missing`), §6, §7
Tasks: T04-01, T04-02, T04-03, T04-04

Written against the owner's answers of 2026-11-18: [Q-15](../RISKS.md#q-15) (Titan Text Embeddings V2, 1024 —
ADR-019; deliberate deviation from W4-G2's 1536) and [Q-20](../RISKS.md#q-20) (interface endpoint created on demand,
no raise on Bedrock failure — ADR-020). Column list: [spec 06](06-users-table-and-migrations.md) §Outputs (single
home); dispatch table: spec 06 §Inputs; the upsert itself: [spec 07](07-user-sync.md).

## Purpose

Every row of `users` gets a 1024-dimensional, unit-length embedding of its profile description, computed by
`aws-challenge-sync` with Amazon Bedrock (Titan Text Embeddings V2) when the user is inserted or updated, and stored in
`users.embedding` with an HNSW index, so that the similarity query of [spec 11](11-similarity-check.md) can rank
users. When Bedrock is unreachable (the endpoint exists only during working sessions) the row is stored without a
vector, quickly and without a function error; rows without a vector are filled by an owner-invoked back-fill.

## Inputs

**Migration** `lambdas/sync/migrations/V2__add_users_embedding.sql` (rules of spec 06): extension `vector`, column
`users.embedding vector(1024)` nullable, index `users_embedding_hnsw_idx` `USING hnsw (embedding vector_l2_ops)`.

**Embedding text** — built from the mapped column values of the row (spec 07 §Outputs), parts in this order, a part
left out when its value is NULL, parts joined with `"; "`:

| Part | Format |
|---|---|
| gender | `gender: <gender>` |
| birthdate | `birth year: <YYYY>` |
| country | `country: <country>` |
| height_cm | `height: <n> cm` |
| weight_kg | `weight: <n> kg` |

E-mail, names, ids and timestamps are never part of the text. All five NULL → no text (outcome `skipped`).

**Bedrock request** — `InvokeModel` on `bedrock-runtime` in the function's region (boto3 default endpoint; private DNS
of the interface endpoint), `modelId` `amazon.titan-embed-text-v2:0` (code constant; confirmed by the T04-01
evidence), `contentType`/`accept` `application/json`, body (one text per call):
`{"inputText": "<text>", "dimensions": 1024, "normalize": true, "embeddingTypes": ["float"]}`.
Response field used: `embedding` (list of floats).

**Bedrock client** — created lazily once per execution environment (no network call at init): `connect_timeout` 2 s,
`read_timeout` 5 s, `retries` `{"mode": "standard", "total_max_attempts": 1}` (no retry).

**Direct invoke** `{"action":"embed-missing"}` (console Test tab, owner); exactly this one key, else
`EMBED_BAD_REQUEST`.

**Configuration:** none new (no env var; the model id and dimension are code constants; region from `AWS_REGION`).

## Outputs

**Stored vector:** the model's float vector, checked (exactly 1024 finite values, norm > 0) and scaled to Euclidean
length 1 (each component divided by the norm — a no-op within rounding for Titan's normalised output), written as
`CAST(:embedding AS vector)` with the text form `[x1,x2,…,x1024]`.

**Upsert (spec 07) additions:** the upsert sets `embedding` on insert and overwrites it on conflict (NULL when
`skipped` or `failed`). The return value of spec 07 is unchanged (`{"outcome": "inserted"|"updated"}`) also when the
embedding failed.

**Error classes** (`errorClass` in the log; never a value or foreign text):

| Bedrock outcome | `errorClass` |
|---|---|
| connection not possible (`ConnectTimeoutError`, `EndpointConnectionError` — endpoint absent, SG blocks 443) | `UNREACHABLE` |
| read timeout | `TIMEOUT` |
| AWS error response | the AWS error code (e.g. `ThrottlingException`, `AccessDeniedException`, `ValidationException`) |
| missing/wrong-length/non-finite/zero vector | `BAD_RESPONSE` |

**Result of `embed-missing`:** `{"embedded": n, "skipped": n, "failed": n, "remaining": n, "stopped": "<reason>"}` —
counts of this run; `remaining` = rows with `embedding IS NULL` and at least one of the five text fields, after the
run; `stopped` = `done` (every selected row processed; `remaining` > 0 then only for `BAD_RESPONSE` rows or rows
beyond the 1000-row limit), `time_budget` (remaining function time < 10 s) or `bedrock_error: <errorClass>`
(the first non-row Bedrock error, i.e. any class except `BAD_RESPONSE`).

**Function errors** (Lambda error message):

| Case | Message |
|---|---|
| `embed-missing` with any other key or value | `EMBED_BAD_REQUEST` |
| DB connection / SQL error in `embed-missing` | `DB_CONNECT_FAILED` / `EMBED_FAILED: <SQLSTATE\|UNKNOWN>` |

A Bedrock failure is **never** a function error — neither on the `UserConfirmed` path nor in `embed-missing`.

**Log lines** (one JSON object per invocation):

| Path | Fields added to the existing line |
|---|---|
| `UserConfirmed` upsert (spec 07 line) | `embedding` (`stored` / `skipped` / `failed`), `bedrockMs`, `errorClass` on a Bedrock failure |
| `embed-missing` | `level`, `message`, `function`, `awsRequestId`, `action`, `embedded`, `skipped`, `failed`, `remaining`, `stopped`, `bedrockCalls`, `bedrockMs`, `outcome`, `durationMs`, `errorClass` |

Never logged: the embedding text, the vector, any attribute value, e-mail.

## Behaviour

1. Owner applies V2 with `{"action":"migrate"}` → `{"applied":[2],"current":2}` (no Bedrock call, no endpoint needed).
2. `UserConfirmed`: after validation and mapping (spec 07), sync builds the text; no text → `skipped`, no Bedrock
   call. Otherwise one `InvokeModel` **before** the DB connection; checks and normalises the vector.
3. Sync runs the upsert with the vector, or NULL when `skipped`/`failed`, and returns `{"outcome": …}` as before. A
   Bedrock failure is only logged (`embedding` `failed`, `errorClass`); the function does not raise, so neither
   Lambda nor EventBridge retries the event.
4. `embed-missing`: select rows `WHERE embedding IS NULL ORDER BY id` (at most 1000 per run); rows without text →
   `skipped`; for each other row, while the function's remaining time is ≥ 10 s: one `InvokeModel`, then
   `UPDATE users SET embedding = CAST(:e AS vector) WHERE id = :id AND embedding IS NULL` (does not touch
   `updated_at`; committed per row). `BAD_RESPONSE` → the row counts as `failed`, the run continues; any other
   Bedrock error → the row counts as `failed` and the run **stops** (`stopped` = `bedrock_error: <errorClass>`), so an
   absent endpoint costs one connect timeout, not one per row.
5. Connection closed in `finally`; one log line.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| Endpoint absent (between sessions) | `UserConfirmed`: one connect timeout (expected 2–6 s), row upserted with NULL, log `embedding` `failed`, `errorClass` `UNREACHABLE`, no function error, no retry; `embed-missing`: `failed` 1, `stopped` `bedrock_error: UNREACHABLE`, returns within 15 s |
| SG of the endpoint blocks 443 | same as endpoint absent (`UNREACHABLE`) |
| Model access missing / wrong model id | `AccessDeniedException` / `ValidationException` → row stored with NULL (log `errorClass`); `embed-missing` stops at the first row |
| Throttling | `UserConfirmed`: NULL, log `ThrottlingException`; `embed-missing` stops; the owner re-runs later |
| Response vector length ≠ 1024, non-finite value or all zeros | `BAD_RESPONSE`, nothing stored for that row |
| Re-sync of an existing user, Bedrock reachable | vector recomputed and overwritten |
| Re-sync of an existing user, Bedrock unreachable | vector set to NULL (no stale vector), filled by the next `embed-missing` |
| Row with all five fields NULL | `skipped`, stays NULL, not counted in `remaining` |
| `embed-missing` with nothing to do | `{"embedded":0,"skipped":0,"failed":0,"remaining":0,"stopped":"done"}`, no Bedrock call |
| More rows than fit in one run | `stopped` `time_budget`, `remaining` > 0; the owner repeats |
| `embed-missing` run while a `UserConfirmed` writes the same row | the `AND embedding IS NULL` guard keeps the newer vector |
| V2 applied twice | runner: nothing pending (spec 06); `IF NOT EXISTS` only for the extension |

## Acceptance Criteria

AWS-side criteria are verified from evidence the owner provides (Test-tab outputs, log lines, screenshots); agents
have no AWS access (CLAUDE.md §3.11). AC-10.1 and AC-10.2 are verified locally.

- [ ] AC-10.1 `V2__add_users_embedding.sql` creates exactly the extension `vector`, the nullable column
  `users.embedding vector(1024)` and the index `users_embedding_hnsw_idx` (`hnsw`, `vector_l2_ops`); V1 is
  byte-identical; the optional integration test applies V1+V2 on local PostgreSQL 14 + pgvector
- [ ] AC-10.2 `pytest` for `lambdas/sync` passes and covers: the text template (order, missing parts, no e-mail/names,
  all-NULL → `skipped` without a Bedrock call); model id and request body exactly as §Inputs; client config
  (connect 2 s, read 5 s, one attempt); normalisation (unit length; zero/short/non-finite vector → `BAD_RESPONSE`);
  error-class mapping (connect/endpoint errors → `UNREACHABLE`, read timeout → `TIMEOUT`, AWS code); upsert with the
  vector as a parameter (no value in the SQL text) and with NULL on failure; Bedrock failure → row upserted, normal
  return, **no exception**; Bedrock call before the DB connection; `embed-missing` (one call per row, counts,
  `remaining` excludes text-less rows, `BAD_RESPONSE` continues, other error stops after one call, time budget,
  bad request); dispatch of the new action; log lines without text, vector or attribute values; all spec 06/07 tests
  still green
- [ ] AC-10.3 Test-tab `{"action":"migrate"}` → `{"applied":[2],"current":2}`, then `{"action":"status"}` →
  `{"current":2,"pending":[]}` (W4-G1, S1, S3)
- [ ] AC-10.4 End to end (endpoint present): a new user signs up in the SPA and is confirmed by the owner; within
  1 minute the sync log shows `inserted` with `embedding` `stored` and `bedrockMs` for that `userSub`; a `similar`
  check with that user's id (spec 11) returns it first with distance ≈ 0 (W4-G2, S2)
- [ ] AC-10.5 `{"action":"embed-missing"}` (endpoint present) repeated until `remaining` is 0; the result of each run
  and its log line are recorded (existing users back-filled)
- [ ] AC-10.6 The sync role has `bedrock:InvokeModel` only on the foundation-model ARN of
  `amazon.titan-embed-text-v2:0` in eu-west-1; the sync log lines of AC-10.4/AC-10.5/AC-10.7 contain no embedding
  text, vector, e-mail or attribute value (owner screenshots, account id masked)
- [ ] AC-10.7 Fail fast with the endpoint absent: a `UserConfirmed` event (a new confirmation or the re-sync sample
  event of the `user-sync` skill) → no function error and no retry; the row is upserted; the log line shows `embedding`
  `failed`, `errorClass` `UNREACHABLE` and `durationMs` < 15000; `{"action":"embed-missing"}` returns within 15 s with
  `stopped` `bedrock_error: UNREACHABLE`; after the endpoint is created again, `embed-missing` stores the missing
  vector (`remaining` 0)
