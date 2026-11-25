---
name: bedrock-embeddings
description: How this project computes and stores user profile embeddings with Amazon Bedrock Titan Text Embeddings V2 in the Lambda aws-challenge-sync — model id, request body, 1024 dimensions, defensive normalisation, the fail-fast bedrock-runtime client (connect 2 s, read 5 s, one attempt), the errorClass mapping, why a Bedrock failure never raises, the owner actions embed-missing / seed / similar on the sync Test tab, IAM and the on-demand VPC endpoint (pointers), and how to test locally with the StubBedrock double. Use when changing lambdas/sync/embeddings.py or vectors.py, the embedding step of the upsert, writing a runbook that deploys sync or runs the vector actions, or reviewing evidence for spec 10 / spec 11.
license: MIT
metadata:
  domain: backend
  triggers: Bedrock, bedrock-runtime, InvokeModel, Titan, amazon.titan-embed-text-v2:0, embedding, embeddings.py, vectors.py, pgvector, vector(1024), embed-missing, seed, similar, HNSW, UNREACHABLE, BAD_RESPONSE, vpce, aws-challenge-vpce-bedrock-runtime
  role: specialist
  scope: implementation
  related-skills: python-lambda, user-sync, postgres-migrations, postgres-pro
  source: project (created by T04-02)
  used-by: [backend, devops, tester]
---

# Bedrock embeddings in `aws-challenge-sync`

Decisions: ADR-019 (Titan Text Embeddings V2, 1024 dimensions, normalised, HNSW `vector_l2_ops`, query `<->`), ADR-020
(on-demand `bedrock-runtime` interface endpoint, fail fast, never raise on a Bedrock failure); design
[vectorisation](../../../docs/design/vectorisation.md). Contracts (single homes — link, never copy): text template,
request, client config, error classes, `embed-missing`, log fields → [spec 10](../../../docs/specs/10-embeddings.md);
`seed`, `similar` → [spec 11](../../../docs/specs/11-similarity-check.md); dispatch table and column list →
[spec 06](../../../docs/specs/06-users-table-and-migrations.md). Deployed names (endpoint, security group, policy):
[ENVIRONMENT.md](../../../docs/ENVIRONMENT.md). Code conventions, tests, packaging: [python-lambda](../python-lambda/SKILL.md).

## Code map (`lambdas/sync/`)

| File | What |
|---|---|
| `embeddings.py` | `MODEL_ID`, `DIMENSIONS` (code constants, no env var); `build_text(row)`; lazy client `_bedrock()`; `embed(text)` → unit-length `list[float]` or `EmbeddingError(<errorClass>)`; `normalise`; `to_vector_literal` |
| `user_sync.py` | upsert: `_embedding(params, state)` runs **before** `db.connect()`; result goes into `CAST(:embedding AS vector)` (NULL when skipped/failed) |
| `vectors.py` | owner actions `embed-missing`, `seed`, `similar` (`handle`), reached from the dispatcher for exactly these three `action` values |
| `migrations/V2__add_users_embedding.sql` | extension `vector`, column, HNSW index (postgres-migrations skill) |

## Rules

- **Dependency:** `boto3`/`botocore` from the Lambda Python 3.12 runtime (`bedrock-runtime` is in every botocore
  since 1.31.57, Sept 2023); never in `requirements.txt`. The local pin in `lambdas/requirements-dev.txt` is for tests.
- **Client:** created on first use, once per execution environment; region `AWS_REGION`; default endpoint URL (private
  DNS of the interface endpoint resolves it inside the VPC — no endpoint URL in code or configuration);
  `Config(connect_timeout=2, read_timeout=5, retries={"mode": "standard", "total_max_attempts": 1})`.
- **Request:** one text per `InvokeModel`; `contentType`/`accept` `application/json`; body exactly as spec 10.
- **Response:** `embedding` must be a list of exactly 1024 finite numbers with norm > 0; it is divided by its norm
  (Titan already normalises — a no-op within rounding) and written as the text form `[x1,…,x1024]` **as a parameter**.
- **Error mapping (`embeddings._error_class`):** botocore `ReadTimeoutError` → `TIMEOUT`; any botocore
  `ConnectionError` (`ConnectTimeoutError`, `EndpointConnectionError`, SSL/proxy errors) → `UNREACHABLE`;
  `ClientError` → its AWS error code (sanitised to an identifier, else `ClientError`); bad response → `BAD_RESPONSE`;
  anything else → the exception class name (e.g. `NoCredentialsError`, `KeyError` for a missing `AWS_REGION`).
  `str(EmbeddingError)` is the class only — never a foreign message.
- **Never raise on the upsert path:** a failure stores NULL, logs `embedding: failed` + `errorClass` and returns
  `{"outcome": …}` normally, so Lambda does not retry the async event (ADR-020). DB errors still raise (spec 07).
  When both fail, the log's `errorClass` is the DB error; `embedding` still says `failed`.
- **`embed-missing`:** rows `embedding IS NULL ORDER BY id LIMIT 1000`; text-less rows `skipped` (no call, not in
  `remaining`); before each call check `context.get_remaining_time_in_millis() >= 10000` (else `time_budget`); per-row
  `UPDATE … AND embedding IS NULL` in autocommit; `BAD_RESPONSE` continues, any other class stops the run
  (`bedrock_error: <class>`, log `WARNING`, still a normal return).
- **`seed`:** per-user `random.Random("seed-<k>")` (SHA-512 seeded, stable across processes and Python 3.12/3.13), so
  user `k` is the same whatever `count`; `uuid5(SEED_NAMESPACE, "seed-<k>")`; batches of 100 rows per parameterised
  `INSERT … ON CONFLICT (id) DO NOTHING RETURNING 1` in one transaction; no vectors (run `embed-missing` afterwards).
  Synthetic rows are identified by the `seed.invalid` e-mail domain (R-17); deleting them is not implemented.
- **`similar`:** stored vector read as text and passed back as `:q`; items with a NULL distance are dropped (a
  sequential scan returns rows without a vector last); `EXPLAIN (ANALYZE, FORMAT JSON)` twice inside one transaction
  (`SET LOCAL enable_seqscan = off` before the second), always `ROLLBACK`. `parse_plan` reports the first `… Scan` node
  (`<Node Type> using <Index Name>`) and `Execution Time`.
- **DB timeouts:** upsert keeps the shared 10 s; the three actions use `vectors.DB_TIMEOUT_S` = 30 s (< 60 s function
  timeout).
- **Logs:** never the embedding text, the vector, attribute values, e-mail or result ids — counts, timings, classes.

## IAM and network (owner, console runbooks — pointers only)

- Sync role: `bedrock:InvokeModel` on `arn:aws:bedrock:<region>::foundation-model/amazon.titan-embed-text-v2:0` only
  (design §Security; T04-01 runbook; ids in ENVIRONMENT.md).
- Endpoint `aws-challenge-vpce-bedrock-runtime` exists **only during working sessions** (create/delete procedure:
  T04-01 runbook). Without it every call ends as `UNREACHABLE` after the 2 s connect timeout (a few seconds in
  total) — expected, not an incident: run `{"action":"embed-missing"}` in the next session.
- Model access for Titan V2 is an Amazon model (no Marketplace subscription).

## Owner Test-tab sequence (runbook building blocks for devops)

1. Upload the sync zip; `{"action":"migrate"}` → V2 applied (postgres-migrations skill).
2. Create the endpoint (T04-01 procedure). `{"action":"embed-missing"}` → repeat until `remaining` is 0
   (`stopped` `time_budget` means "run again"; `bedrock_error: UNREACHABLE` means the endpoint is missing or the SG
   blocks 443).
3. `{"action":"seed","count":1000}` → `{"inserted":…, "seeded":1000}`; then step 2 again (≈ 1–3 min of calls in total).
4. `{"action":"similar","userId":"<uuid>"}` → top 5, `default`/`indexForced` scan and `executionMs` (S4 evidence).
5. Delete the endpoint at the end of the session.

## Testing locally

```powershell
.venv\Scripts\python -m pytest lambdas/shared lambdas/sync
```

- `tests/bedrock_stub.py`: `StubBedrock(outcomes=[…], default=…)` records `invoke_model` kwargs and answers with a
  vector list, raw bytes or a raised exception (real botocore exception classes); `install(monkeypatch, stub)`
  replaces `embeddings._bedrock_client`. `test_user_sync.py` installs it for every test (autouse).
- `tests/test_embeddings.py` (template, request, real client config without network, normalisation, error classes),
  `tests/test_vectors.py` (`VectorDb` double: dispatch, `embed-missing`, `seed`, `similar`, plan parsing).
- `tests/test_vectors_integration.py`, `test_user_sync_integration.py`, `test_migrator_integration.py`: optional, real
  PostgreSQL 14 + pgvector (`docker compose up -d`, `MIGRATE_TEST_DATABASE_URL`); they put `public` on the search path
  so an extension already installed there is found.
