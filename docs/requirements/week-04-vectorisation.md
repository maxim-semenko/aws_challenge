# Requirements — Week 4: Data vectorisation

Source: challenge curriculum, "Week 4: Data vectorisation" (Alex Ramasheuski, 2025-09-02), screenshot provided by the
owner on 2026-11-17. Translated to English. This file is the input for design docs and specs; it is not edited except
to fix the export.

## Task (as given)

Add an `embedding` column and compute vectors for the text fields using Amazon Bedrock and pgvector.

## Week goals (as given)

| # | Goal |
|---|---|
| W4-G1 | The pgvector extension is created (`CREATE EXTENSION pgvector`) |
| W4-G2 | A function generates 1536-dimensional vectors and stores them in `users.embedding` |
| W4-G3 | An example similarity query `ORDER BY embedding <-> $1 LIMIT 5` runs |

## Implementation steps (as given)

| # | Step |
|---|---|
| S1 | Enable pgvector on RDS PostgreSQL |
| S2 | Update the Sync Lambda: on insert/update call Bedrock Titan Embeddings or Claude 3.5 Sonnet and get the vector |
| S3 | Add an index `USING ivfflat` or `hnsw` in pgvector |
| S4 | Check the search latency on 1 000 records |

## Materials (as given)

Amazon RDS support for pgvector · DataCamp pgvector tutorial · Deep dive into pgvector (Severalnines) · GitHub pgvector
README · RAG example Bedrock + Claude 3 → SQL.

## Traceability

| Requirement | Spec |
|---|---|
| W4-G1, S1, S3 | [10-embeddings](../specs/10-embeddings.md) (V2: extension `vector`, column, HNSW index) |
| W4-G2, S2 | [10-embeddings](../specs/10-embeddings.md) — Titan Text Embeddings V2, **1024** dimensions: deliberate deviation from the 1536 of W4-G2, decided by the owner 2026-11-18 ([Q-15](../RISKS.md#q-15), ADR-019: the 1536-dim Titan model is not offered in eu-west-1); "Claude 3.5 Sonnet" is not an embedding model |
| W4-G3, S4 | [11-similarity-check](../specs/11-similarity-check.md) (seed 1000 users, example query, latency) |
