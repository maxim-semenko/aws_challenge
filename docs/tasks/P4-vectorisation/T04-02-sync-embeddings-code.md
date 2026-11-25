---
id: T04-02
title: "Sync Lambda: V2 migration (pgvector), embedding on upsert, actions embed-missing / seed / similar (Python, pytest)"
phase: P4-vectorisation
status: Done
agent: backend
skills: [postgres-pro, test-master]
depends_on: []
blocked_by: []
design: ../../design/vectorisation.md
spec: [../../specs/10-embeddings.md, ../../specs/11-similarity-check.md]
acceptance: [AC-10.1, AC-10.2, AC-11.1]
---
# T04-02 — Sync Lambda: pgvector migration, embeddings, similarity check actions

## // BUSINESS CONTEXT

W4-G1…W4-G3, S1…S4: the users table gets 1024-dimensional vectors (Titan Text Embeddings V2; deliberate deviation
from the curriculum's 1536, ADR-019) computed with Bedrock whenever the Sync Lambda inserts or updates a user; the owner can back-fill missing vectors, seed 1000 synthetic users and
run the curriculum's similarity query with its latency — all from the sync Test tab, without a new function.

## // TECHNICAL CONSTRAINTS

- Conventions of the `python-lambda`, `postgres-migrations` and `user-sync` skills; runtime Python 3.12 (no 3.13-only
  API); no network call or DB connection at init; parameterised SQL only.
- `migrations/V2__add_users_embedding.sql` exactly as spec 10 §Inputs; V1 byte-identical (applied checksum).
- Model id `amazon.titan-embed-text-v2:0`, request body, dimension 1024 and client config (connect 2 s, read 5 s,
  one attempt) exactly as spec 10 §Inputs; model id and dimension as code constants, no env var.
- No new dependency: `boto3` `bedrock-runtime` from the Lambda runtime (check the runtime's boto3 version in the AWS
  Lambda runtimes docs and record it in Notes); `requirements.txt` unchanged.
- Dispatcher: only the three new actions go to the new module; every other `action` still reaches `migrator.handle`
  unchanged (spec 06 §Inputs); `UserConfirmed` route and `UNSUPPORTED_EVENT` unchanged.
- Upsert (spec 07 + spec 10): Bedrock before the DB connection; row always upserted; a Bedrock failure is logged
  (`embedding` `failed`, `errorClass`) and **never raised** — the endpoint is absent between sessions (ADR-020), so the
  invocation must end fast and without async retries. `embed-missing`: one call per row, time budget, stop at the
  first non-row Bedrock error (spec 10 §Behaviour 4). DB socket timeouts: upsert keeps the 10 s default; `embed-missing`,
  `seed` and `similar` may use a longer one below the 60 s function timeout.
- Logs per spec 10/11 — no embedding text, vector, attribute value or result id.
- pytest with test doubles (stub Bedrock client, fake DB); optional integration test V1+V2 + `similar` on local
  PostgreSQL 14 + pgvector (`docker compose up -d`).

## // SCOPE

**Implement**
- `lambdas/sync/`: `embeddings.py` (text template, Bedrock client and request, normalisation, errors),
  `vectors.py` (`embed-missing`, `seed`, `similar`), changes to `user_sync.py` and `lambda_function.py`, V2 migration,
  tests covering AC-10.1, AC-10.2, AC-11.1; zip builds (`build/lambdas/sync.zip` hash in Notes)
- Skill `bedrock-embeddings` (new: model, request, normalisation, client config, errors, IAM and endpoint pointers,
  local testing); updates of `postgres-migrations` (V2, extension rights), `user-sync` (embedding in the upsert),
  `python-lambda` (layout); `lambdas/README.md` row text

**Exclude**
- AWS changes (T04-01, T04-03); `chatbot` code and `POST /chat` (Week 5); deleting synthetic users; re-embedding
  rows that already have a vector

**Interfaces that must match**
- Column, index and dispatch: spec 06; contracts: spec 10, spec 11; model id: T04-01 evidence.

## Definition of Done

- [x] pytest green (AC-10.1, AC-10.2, AC-11.1); sync zip builds; 3.12 check stated
- [x] Skills added/updated (done); ARCH review passed (2026-11-18, no blocking findings)
- [ ] Status updated here (`Review`) and in [PLAN.md](../../PLAN.md) (not edited by backend, per instruction)

## Notes

- 2026-11-17: created by Week 4 planning; `Blocked` by Q-15 (model request format and dimension). Q-20 does not
  change the code (boto3 default endpoint).
- 2026-11-18: unblocked — owner answered Q-15 (Titan V2, 1024, ADR-019) and Q-20 (endpoint on demand, fail fast, no
  raise — ADR-020); design vectorisation `Accepted`; spec 10 updated (request, client config, error classes,
  `embed-missing` stop rules, AC-10.7). → `Todo`. The model id is fixed by ADR-019; T04-01 only confirms it.
- 2026-11-18 (backend): start gate held (`Todo`, no dependencies, design `Accepted`) → `In progress` → `Review`.
  - **Code** (`lambdas/sync/`): `embeddings.py` (template, lazy `bedrock-runtime` client connect 2 s / read 5 s /
    `total_max_attempts` 1, request, normalisation, errorClass mapping), `vectors.py` (`embed-missing`, `seed`,
    `similar`; DB socket timeout 30 s), `user_sync.py` (embedding before `db.connect()`, `CAST(:embedding AS vector)`,
    overwritten on conflict, Bedrock failure → NULL + log, never raised), `lambda_function.py` (only the three new
    actions go to `vectors.handle`), `migrations/V2__add_users_embedding.sql` (SHA-256 `df89214e…a030de88`, LF).
    V1 byte-identical: SHA-256 `9800e6e7…44fa9a5c7` = T03-03 applied checksum (now pinned by a test).
    `requirements.txt` unchanged (`fd976ede…d7fd5d45`); no new dependency.
  - **Choices within the spec** (for the review): a non-AWS, non-connection Bedrock exception is logged with its class
    name (e.g. `NoCredentialsError`) and counts as a non-row error (stops `embed-missing`); when Bedrock and the DB
    both fail on the upsert, `errorClass` is the DB error, `embedding` still `failed`; `embedding`/`bedrockMs` are not
    on `rejected` lines; `similar` drops items with NULL distance (rows without vector under a seq scan) so the query
    text stays the curriculum's; `embed-missing` `stopped` is `done` when all selected rows were processed (rows with
    `BAD_RESPONSE` stay in `remaining`).
  - **Tests** (temp venv outside the repo, `py -3.13`, boto3 1.44.3 / botocore 1.44.5, pytest 9.2.0):
    `pytest lambdas/shared lambdas/sync` → **238 passed, 3 skipped** (the three integration tests; Docker Desktop not
    running → **AC-10.1 local DB run and the `similar` integration test not verified**). Other suites unchanged and
    green: `lambdas/shared lambdas/admin` 104 passed, 6 skipped; `lambdas/post-confirmation` 13 passed;
    `lambdas/tests` 7 passed. New: `test_embeddings.py`, `test_vectors.py`, `bedrock_stub.py`,
    `test_vectors_integration.py`; updated: `test_user_sync.py` (spec 10 upsert cases), `test_migrator.py` (V1 hash,
    V2 statements, packaged V1+V2), both existing integration tests (V2, search path `<schema>, public`).
  - **Build:** `py -3.13 lambdas/package.py sync` → `build/lambdas/sync.zip`, **96 files, 443235 bytes**, SHA-256
    hex `03ab9a349ce5a87b29d6d7c6818f91a6281d8d26a9ff62dda023ea75f24cd676`, base64
    `A6uaNJzlqHsp1tfGgY+RpigdjSap/2LdoCPqdfJM1nY=` (Lambda console "Code SHA-256"); identical on rebuild; root
    contains `embeddings.py`, `vectors.py`, `migrations/V1…`, `migrations/V2…`; no tests or `.pyc`.
  - **3.12 check:** static check only — no 3.13-only API (`from __future__ import annotations`, PEP 604 unions,
    `random.Random(str)` (SHA-512 seeding, same in 3.12), `math.fsum`, `uuid.uuid5`).
  - **Runtime boto3:** not verified — the AWS "Runtime-included SDK versions" table could not be read by the agent.
    `bedrock-runtime` exists since boto3 1.28.57 / botocore 1.31.57 (Sept 2023), older than the Python 3.12 runtime
    (Dec 2023), so any 3.12 runtime build has it; `total_max_attempts` in `Config.retries` is older still. T04-03 may
    confirm by the first `embedding: stored` log line.
  - **Skills:** new `bedrock-embeddings`; updated `postgres-migrations` (V2, extension rights, LF, integration search
    path), `user-sync` (embedding in the upsert, stub), `python-lambda` (layout); `lambdas/README.md` sync row.
  - **ACs:** AC-10.1 static part (V2 statements, V1 hash) verified by pytest, DB part not verified (no Docker);
    AC-10.2 and AC-11.1 verified by pytest (the listed cases are in `test_embeddings.py`, `test_user_sync.py`,
    `test_vectors.py`). Nothing deployed; no AWS access.
- **ARCH review 2026-11-18: pass (no blocking findings).** Re-run in a temp venv (`py -3.13`, `requirements-dev.txt`
  + `sync/requirements.txt`): `lambdas/shared lambdas/sync` 238 passed, 3 skipped; `lambdas/shared lambdas/admin` 104
  passed, 6 skipped; `post-confirmation` + `lambdas/tests` 20 passed. `package.py sync` → SHA-256 `03ab9a34…f24cd676`,
  96 files, no tests/`.pyc` (matches). V1 SHA-256 `9800e6e7…44fa9a5c7` unchanged (not modified in Git).
  - V2 correct for RDS 14.18 / pgvector 0.8.0: extension created by the master user (`DB_USER=postgres`, ENVIRONMENT
    §Lambda; has `rds_superuser`); type and index usable in the same transaction; HNSW supports 1024 dims (limit
    2000); `vector_l2_ops` matches `<->`; index build on the empty table is trivial. Not run against a database
    (Docker not running) — AC-10.1 DB part and `test_vectors_integration.py` **not verified**; local image is pgvector
    0.8.7, RDS 0.8.0 (no difference for these statements); AC-10.3 on RDS is the real proof.
  - Accepted as within spec: client config and errorClass mapping; Bedrock before `db.connect()`; nothing on the
    upsert path raises on a Bedrock failure (`_bedrock()` creation is inside the `try`); vector only as a parameter;
    seed/similar SQL parameterised (only constants formatted), 100 rows × 10 params per insert, `.invalid` e-mails;
    `SET LOCAL` inside a rolled-back transaction; logs carry counts/timings/classes only; 3.12-compatible. The five
    backend choices in Notes are accepted; spec 10 §Outputs `stopped: done` wording aligned with choice 5.
  - Non-blocking: (1) `vectors.py:41-44` — rows without text (and repeated `BAD_RESPONSE` rows) stay in the
    `ORDER BY id LIMIT 1000` window, so ≥ 1000 of them would starve the back-fill; unlikely here (SPA and seed always
    set attributes) — revisit only if `remaining` stalls. (2) `user_sync.py:187-191` — when Bedrock and the DB both
    fail, the Bedrock `errorClass` is replaced by the DB one (`embedding` `failed` stays); accepted. (3) Runtime boto3
    version not recorded (constraint asks for it) — T04-03 records it from the first `embedding` `stored` line or the
    runtime docs. (4) First packager run in the review aborted with `name clash … embeddings.py` because
    `package.py:95` `rmtree(..., ignore_errors=True)` left a stale staging dir (concurrent run / file lock); the guard
    failed safe and a rerun gave the expected hash — outside this task's scope (T03 packager).
- 2026-11-25: set to `Done` by the owner (Week 4 closed).
