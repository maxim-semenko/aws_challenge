---
id: T04-04
title: "Week 4 acceptance check"
phase: P4-vectorisation
status: Done
agent: tester
skills: [test-master]
depends_on: [T04-01, T04-02, T04-03]
blocked_by: []
design: null  # acceptance task, verifies specs 10-11 and the spec 06/07 regressions
spec: [../../specs/06-users-table-and-migrations.md, ../../specs/07-user-sync.md, ../../specs/10-embeddings.md, ../../specs/11-similarity-check.md]
acceptance: [AC-10.1, AC-10.2, AC-10.3, AC-10.4, AC-10.5, AC-10.6, AC-10.7, AC-11.1, AC-11.2, AC-11.3, AC-11.4, AC-06.2, AC-07.2, AC-07.4]
---
# T04-04 — Week 4 acceptance check

## // BUSINESS CONTEXT

Week 4 ("Data vectorisation") is done when the extension, the vectors (1024-dimensional Titan V2 — the deliberate
deviation from W4-G2's 1536 is stated in the report, ADR-019), the index, the example query and its latency on 1000
records are proven on `dev` by someone other than the implementer. The report is what the
owner shows to the mentor.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11). Local ACs (pytest, zip build, repository contents, `git grep` for
  secrets) run by the tester; AWS-side ACs from owner evidence already in T04-01 … T04-03 Notes (by pointer), only
  missing evidence requested.
- Each AC: pass / fail / not verifiable + source + trimmed output; account ids masked; no personal data.
- Regression: AC-06.2, AC-07.2 (pytest), AC-07.4 (a new confirmation still inserts the row — shown by AC-10.4).

## // SCOPE

**Implement**
- Owner checklist for missing evidence; report table AC → result → evidence in Notes; requirement coverage W4-G1 …
  W4-G3, S1 … S4

**Exclude**
- Fixing defects (reported to the owning task); E2E suite

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All listed ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-17: created by Week 4 planning; `Todo` (no open blocker of its own; waits for T04-01 … T04-03 `Done`).
- 2026-11-18: AC-10.7 (fail fast with the endpoint absent) added after the owner's Q-20 decision.
- 2026-11-25 (tester): acceptance run. Start gate: T04-01 … T04-03 are `Review`, not `Done` — the owner ran the
  session on review-pending work (T04-03 Notes 2026-11-18); report written on that basis. → `In progress` → `Review`.

### Acceptance report — Week 4 (2026-11-25)

**Local runs (tester).** Temp venv outside the repo, `py -3.13` (3.13.2), `lambdas/requirements-dev.txt` +
`lambdas/sync/requirements.txt` (boto3 1.44.3, botocore 1.44.11, pg8000 1.31.6, pytest 9.2.0):

| Command | Result |
|---|---|
| `pytest lambdas/shared lambdas/sync` | **238 passed, 3 skipped** — skips: the three integration tests (`MIGRATE_TEST_DATABASE_URL not set`; Docker Desktop not running) |
| `pytest lambdas/shared lambdas/admin` | 104 passed, 6 skipped (integration) |
| `pytest lambdas/post-confirmation lambdas/tests` | 20 passed |
| `py -3.13 lambdas/package.py sync`, twice | `96 files`; SHA-256 `03AB9A34…F24CD676` both times = T04-02 build = console hash `A6uaNJzl…` uploaded in T04-03 step 1 (deployed artefact = tested artefact) |
| `V1__create_users.sql` | SHA-256 `9800E6E7…44FA9A5C7` = applied checksum; no diff in Git |
| `V2__add_users_embedding.sql` | exactly three statements: `CREATE EXTENSION IF NOT EXISTS vector`, `ADD COLUMN embedding vector(1024)` (nullable), `CREATE INDEX users_embedding_hnsw_idx … USING hnsw (embedding vector_l2_ops)` |
| Secret / account-id scan (tracked and untracked files under `lambdas`, `docs`, `.claude`) | no access key, private key, password literal or 12-digit account ARN (only the test placeholder `000000000000`) |

**AC table.** Owner evidence by pointer: T04-01 Notes (2026-11-18, 2026-11-25), T04-03 Notes (2026-11-18,
2026-11-25). "Accepted on functional evidence" = the literal evidence step was not run, but the behaviour is
demonstrated by other recorded results; proposed to the owner for acceptance.

| AC | Result | Evidence |
|---|---|---|
| AC-10.1 | pass | Tester: V2 content and V1 hash above; `test_migrator.py` (V1 hash pinned, V2 statements) green. Optional local DB run not done (no Docker); the real apply on RDS 14.18 succeeded (AC-10.3) |
| AC-10.2 | pass | Tester: sync suite 238 passed (`test_embeddings.py`, `test_user_sync.py`, `test_vectors.py`, `test_dispatch.py`, `test_migrator.py`); constants checked in code: model id `amazon.titan-embed-text-v2:0`, 1024, connect 2 s / read 5 s / `total_max_attempts` 1 |
| AC-10.3 | pass | Owner (T04-03, 2026-11-18): `status` → `{"current":1,"pending":[2]}`; `migrate` → `{"applied":[2],"current":2}`; `status` → `{"current":2,"pending":[]}` |
| AC-10.4 | accepted on functional evidence | T04-03 step 8 (SPA sign-up with endpoint present) **not run**. Covered by: (a) `UserConfirmed` upsert on AWS works with the V2 code (step 4 row inserted — counted in `remaining` 1002); (b) the deployed function reaches Bedrock and stores Titan V2 vectors through the same `embeddings` module (1002 vectors, 0 failures, step 7); (c) `similar` returns the queried user first with distance 0 (step 9); (d) the stored-on-upsert branch, Bedrock-before-DB order and `bedrockMs` logging are proven by pytest on the byte-identical artefact. Residual: no AWS log line `inserted` + `embedding stored` + `bedrockMs` for a real sign-up |
| AC-10.5 | accepted on functional evidence | Owner (T04-03, 2026-11-25): run 1 `{"embedded":365,"failed":0,"remaining":637,"stopped":"time_budget"}`; last run `{"embedded":246,"failed":0,"remaining":0,"stopped":"done"}`; run 2 not shown (implied `embedded` 391: 365 + 391 + 246 = 1002 = `remaining` of step 5.1). Log lines (Q1) not recorded |
| AC-10.6 | pass (permission) / accepted on functional evidence (log part) | Permission: owner screenshots E3 (T04-01, 2026-11-18) — inline `aws-challenge-sync-bedrock-invoke` on the sync role, no `bedrock:*` / full-access policy; JSON per runbook step 3 (Resource = Titan V2 foundation-model ARN, eu-west-1); no `AccessDeniedException` in the session. Role has 4 policies (also `AWSLambdaVPCAccessExecutionRole`, needed for the VPC) — not a Bedrock grant. Log part: step 11 **not run**; log content proven by pytest (no text, vector, e-mail or attribute value in `embedding` / `embed-missing` / `seed` / `similar` lines) on the artefact whose hash equals the deployed one |
| AC-10.7 | accepted on functional evidence | Owner (T04-03, 2026-11-18, no endpoint): EventBridge Send events → Success; `embed-missing` → succeeded, `{"embedded":0,"skipped":0,"failed":1,"remaining":1002,"stopped":"bedrock_error: UNREACHABLE"}`. The step-4 row exists (in `remaining` 1002) although Bedrock runs before the DB connection — so the handler did not raise on the Bedrock failure; one-attempt / 2 s connect config proven by pytest. After the endpoint was created: `remaining` 0 (2026-11-25). Not captured: Q2 log line (`embedding failed`, `errorClass UNREACHABLE`, `durationMs` < 15000, single line = no retry) and the *Duration* of 5.1 |
| AC-11.1 | pass | Tester: `test_vectors.py` green (generator determinism/ranges, `.invalid` e-mails, idempotent seed, validation, query text `<->` / `LIMIT 5` / `CAST(:q AS vector)`, plan parsing, `SET LOCAL` only in a rolled-back transaction, `SIMILAR_NOT_FOUND`, log lines) |
| AC-11.2 | pass | Owner: `seed` 1000 → `{"inserted":1000,"seeded":1000}` (2026-11-18); `embed-missing` until `remaining` 0 (2026-11-25); `similar` → `rows` 1002, `withEmbedding` 1002 (1000 seeded + 1 real + the AC-10.7 row; 1003 in the runbook assumed step 8) |
| AC-11.3 | accepted on functional evidence | Owner (2026-11-25): `similar` for seeded user 1 → items[0] = `b44b7820-…` with distance 0, items[1] `f8f2d7df-…`. Full list of 5 and ascending order not transcribed; guaranteed by the query (`ORDER BY … LIMIT 5`, 1002 rows with a vector) and pytest |
| AC-11.4 | pass | Owner (T04-03, 2026-11-25): default `Index Scan using users_embedding_hnsw_idx` 0.513 ms; indexForced same index 0.44 ms; recorded in T04-03 Notes (one run; step 9.2 repeats not required by the AC) |
| AC-06.2 | pass | Tester: sync suite green (`test_migrator.py`, `test_dispatch.py`; runner and dispatch cases unchanged) |
| AC-07.2 | pass | Tester: sync suite green (`test_user_sync.py` spec 07 mapping/edge cases, now with the spec 10 additions) |
| AC-07.4 | accepted on functional evidence | Regression "a new confirmation still inserts the row" (via AC-10.4, step 8 not run): the sync `UserConfirmed` path inserted the step-4 row on AWS with the V2 code; `lambdas/post-confirmation`, bus and rule unchanged since Week 3 (no diff in Git, no redeploy), where AC-07.4 passed |

**Counts:** 14 ACs — 9 pass (AC-10.1, 10.2, 10.3, 10.6 permission part, 11.1, 11.2, 11.4, 06.2, 07.2), 5 accepted on
functional evidence (AC-10.4, 10.5, 10.7, 11.3, 07.4; plus the AC-10.6 log part), 0 fail, 0 not verified.

**Requirement coverage:** W4-G1 / S1 — extension `vector` created on RDS (AC-10.3). **W4-G2 — deliberate deviation:
1024-dimensional vectors (Titan Text Embeddings V2) instead of the curriculum's 1536, ADR-019** (owner decision
2026-11-18, Q-15: the 1536-dim Titan G1 model is not offered in eu-west-1 — confirmed by the T04-01 model catalog
screenshot); vectors stored in `users.embedding` for all 1002 rows (AC-10.5, AC-11.2). S2 — sync calls Bedrock on
insert/update (code + pytest; on AWS proven through `embed-missing`, upsert path with a reachable endpoint not shown,
AC-10.4). S3 — HNSW index `users_embedding_hnsw_idx` (AC-10.3, AC-11.4). W4-G3 — the example query
`ORDER BY embedding <-> $1 LIMIT 5` runs (AC-11.3). S4 — latency on 1002 records ≈ 0.5 ms (0.513 default / 0.44
forced, HNSW index used without forcing; AC-11.4).

**Genuinely uncovered (one owner session item each, optional for closing):**
1. AWS log line of a real sign-up with the endpoint present (`inserted`, `embedding stored`, `bedrockMs`) — T04-03
   step 8 (AC-10.4, AC-07.4).
2. Logs Insights Q2 for `…001007` (`embedding failed`, `UNREACHABLE`, `durationMs` < 15000, one line) — T04-03 step
   7 Q2 (AC-10.7); the log group keeps it, so a query is enough, no endpoint needed.
3. One expanded `embedding` / `embed-missing` log line — T04-03 step 11 (AC-10.6 log part); query only, no endpoint
   needed.

**Findings against other tasks (not ACs of this task):**
- T04-01 / T04-03 DoD: ENVIRONMENT.md has no Week 4 entries yet (model id, SG `aws-challenge-vpce-sg` id — not
  reported by the owner, inline policy name, endpoint "on demand", schema V2 applied, 1000 synthetic users) — Low.
- T04-03: endpoint deletion by owner statement only (no screenshot); a second, unnamed interface endpoint
  `vpce-01b735f7…` of unknown origin exists in the account — owner to check (cost) — Low.
- T04-02: runtime boto3 version not recorded; functionally irrelevant now (the deployed runtime called
  `bedrock-runtime` successfully) — Low.
- 2026-11-25: set to `Done` by the owner (Week 4 closed).
