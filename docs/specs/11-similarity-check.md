# Spec 11 — Similarity query and latency check on 1000 records

Requirements: [week-04](../requirements/week-04-vectorisation.md) W4-G3, S3, S4 ·
Design: [vectorisation](../design/vectorisation.md) §1, §5
Tasks: T04-02, T04-03, T04-04

Depends on [spec 10](10-embeddings.md) (column, index, vectors) and the dispatch table of
[spec 06](06-users-table-and-migrations.md) §Inputs. Vectors: Titan Text Embeddings V2, dimension 1024
([Q-15](../RISKS.md#q-15) answered 2026-11-18, ADR-019). `seed` and `similar` make no Bedrock call and work without
the `bedrock-runtime` endpoint (ADR-020); only the `embed-missing` step between them needs it.

## Purpose

The owner can fill `users` with 1000 synthetic users and run the curriculum's example query
`ORDER BY embedding <-> $1 LIMIT 5` from the sync Test tab, getting the top 5, proof that the HNSW index is used, and
the query latency on 1000 records.

## Inputs

**Direct invokes of `aws-challenge-sync`** (console Test tab, owner):

| Event | Field | Type | Valid range | Required |
|---|---|---|---|---|
| `seed` | `action` | string | `seed` | yes |
| | `count` | integer | 1…1000 — target number of synthetic users in total | yes |
| `similar` | `action` | string | `similar` | yes |
| | `userId` | string | UUID of a row with a non-NULL `embedding` | yes |

Any other key, type or value → `SEED_BAD_REQUEST` / `SIMILAR_BAD_REQUEST`.

**Synthetic user generator** (deterministic: same `count` → same rows): user number `k` = 1…`count`; `id` =
`uuid5(<fixed namespace UUID in code>, "seed-<k>")`; `email` = `seed-<k, 4 digits>@seed.invalid`; `given_name`,
`family_name` from fixed lists of fictitious names; `gender` `female`/`male`; `birthdate` 1950-01-01…2007-12-31;
`country` from a fixed list of countries; `height_cm` 140…210; `weight_kg` 40…150 (SPA ranges, spec 04);
`confirmed_at` = time of the seed; `embedding` NULL.

## Outputs

| Case | Return value / error |
|---|---|
| `seed` | `{"inserted": n, "seeded": total}` — `n` rows inserted now (`ON CONFLICT (id) DO NOTHING`), `total` = synthetic rows present (e-mail domain `seed.invalid`) |
| `similar` | `{"rows": n, "withEmbedding": n, "items": [{"id": "<uuid>", "distance": <float>}, … max 5], "default": {"scan": "<node>", "executionMs": <float>}, "indexForced": {"scan": "<node>", "executionMs": <float>}}` |
| `similar`, `userId` unknown or its `embedding` NULL | function error `SIMILAR_NOT_FOUND` |
| bad request | `SEED_BAD_REQUEST` / `SIMILAR_BAD_REQUEST` |
| DB error | `DB_CONNECT_FAILED` / `SEED_FAILED: <SQLSTATE\|UNKNOWN>` / `SIMILAR_FAILED: <SQLSTATE\|UNKNOWN>` |

`scan` = node type and index name of the scan node in the plan (e.g. `Index Scan using users_embedding_hnsw_idx`,
`Seq Scan`); `executionMs` = the plan's `Execution Time`. `items` contain ids and distances only.

**Query** (single statement, the curriculum's form; `$1` = the user's stored vector, passed as a parameter):
`SELECT id, embedding <-> CAST(:q AS vector) AS distance FROM users ORDER BY embedding <-> CAST(:q AS vector) LIMIT 5`.

**Log line:** `level`, `message`, `function`, `awsRequestId`, `action`, `outcome`, `durationMs`, `errorClass`; `seed`
adds `inserted`, `seeded`; `similar` adds `rows`, `withEmbedding`, `defaultScan`, `defaultMs`, `indexScan`, `indexMs`.
Never ids of the result, vectors or attribute values.

## Behaviour

1. `seed`: generate users 1…`count` and insert them in one transaction with parameterised multi-row inserts; no
   Bedrock call. The owner then runs `{"action":"embed-missing"}` (spec 10; one Titan call per row, so a few runs for
   1000 rows) with the endpoint present until `remaining` is 0.
2. `similar`: read the user's vector; run the query (items); then in one transaction `EXPLAIN (ANALYZE, FORMAT JSON)`
   of the same query with the planner's defaults, and again after `SET LOCAL enable_seqscan = off`; `ROLLBACK`
   (settings never outlive the call). The first item is the user itself (distance 0).
3. Latency evidence for S4 = `default.executionMs` and `indexForced.executionMs` with `rows` ≥ 1000.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| `seed` repeated with the same `count` | `inserted: 0`, same `seeded` |
| `seed` with a smaller `count` than before | inserts nothing, deletes nothing |
| Planner prefers `Seq Scan` on ~1000 rows | `default.scan` = `Seq Scan` (valid, reported); `indexForced.scan` uses `users_embedding_hnsw_idx` |
| Rows with NULL embedding | never returned by the index scan; after `embed-missing` none remain |
| Fewer than 5 rows with a vector | `items` shorter than 5 |
| `count` 0, 1001, `"10"` (string), extra key | `SEED_BAD_REQUEST` |

## Acceptance Criteria

AC-11.1 is verified locally; the rest from owner evidence (Test-tab results, log lines).

- [ ] AC-11.1 `pytest` for `lambdas/sync` passes and covers: generator determinism and value ranges, `*.invalid`
  e-mails, idempotent `seed`, request validation of both actions, the query text (`<->`, `LIMIT 5`, vector as a
  parameter), plan parsing (`scan`, `executionMs`) from sample `EXPLAIN` JSON, `SET LOCAL` only inside a rolled-back
  transaction, `SIMILAR_NOT_FOUND`, log lines without ids, vectors or values
- [ ] AC-11.2 `{"action":"seed","count":1000}` → `seeded` 1000; then `embed-missing` until `remaining` 0; `similar`
  shows `rows` ≥ 1000 and `withEmbedding` = `rows` (minus `skipped` rows, if any) (S4 data set)
- [ ] AC-11.3 `{"action":"similar","userId":"<a seeded or real user>"}` returns 5 items, the first is that user with
  distance ≈ 0, distances ascending (W4-G3)
- [ ] AC-11.4 The same result shows `indexForced.scan` = `Index Scan using users_embedding_hnsw_idx` and both
  `executionMs` values; the owner records them in the T04-03 Notes as the latency on 1000 records (S3, S4)
