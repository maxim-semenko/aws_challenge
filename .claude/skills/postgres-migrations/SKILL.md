---
name: postgres-migrations
description: How this project changes the PostgreSQL schema — versioned SQL files lambdas/sync/migrations/V<n>__<description>.sql applied by the runner module inside the Lambda aws-challenge-sync (ADR-017 revised; there is no migrate function), the runner rules (order, one transaction per file, schema_migrations checksums, advisory lock), its results and errors, how the owner runs it from the sync function's console Test tab and how to fix forward. Use when adding a migration, changing the runner or the sync dispatch, reviewing SQL for PostgreSQL 14 compatibility or writing the runbook that deploys sync or invokes a migration.
license: MIT
metadata:
  domain: database
  triggers: migration, schema, V1__create_users.sql, V2__add_users_embedding.sql, pgvector, CREATE EXTENSION, schema_migrations, migrator.py, aws-challenge-sync, migrate, status, UNSUPPORTED_EVENT, MIGRATION_CHECKSUM_MISMATCH, MIGRATION_LOCKED, MIGRATION_FAILED, Flyway naming, fix forward, PostgreSQL 14
  role: specialist
  scope: implementation
  related-skills: python-lambda, postgres-pro
  source: project (created by T03-02)
  used-by: [backend, devops, tester]
---

# PostgreSQL migrations

Decision: ADR-017 (Q-16 A, revised 2026-11-16: no `aws-challenge-migrate`, the runner lives in `aws-challenge-sync`).
Contract — event dispatch, inputs, result values, error strings, table columns, log line:
[spec 06](../../../docs/specs/06-users-table-and-migrations.md) (single home; link, never copy). Code:
`lambdas/sync/migrator.py` (runner, entry `handle(event, context)`), reached from `lambdas/sync/lambda_function.py`
(dispatch); packaging and tests: [python-lambda](../python-lambda/SKILL.md).

## Writing a migration

- File `lambdas/sync/migrations/V<n>__<description>.sql`: `<n>` = next integer (1..n, no gap, no leading zero),
  `<description>` `[a-z0-9_]+`, UTF-8, **LF line endings** (`.gitattributes` `lambdas/** text eol=lf`; a CRLF checkout
  would change the checksum). Nothing else may be in the directory (any other file → `MIGRATION_INVALID_FILES`).
- Applied so far: V1 `users` (Week 3), V2 extension `vector` + `users.embedding vector(1024)` + HNSW index
  `users_embedding_hnsw_idx` (`vector_l2_ops`) (Week 4, spec 10; bedrock-embeddings skill). `test_migrator.py` pins
  the V1 SHA-256 and checks V2 statement by statement.
- **Extensions:** `CREATE EXTENSION IF NOT EXISTS <name>` inside the migration; it needs `rds_superuser` on RDS (the
  proxy DB user is the master user, which has it) and the extension must be in the RDS 14 allow-list (pgvector 0.8.0
  on RDS 14.18; the local image `pgvector/pgvector:0.8.7-pg14` — use no feature newer than 0.8.0). `IF NOT EXISTS`
  only for the extension; tables, columns and indexes fail loudly if they already exist.
- **PostgreSQL 14 syntax only** (RDS is 14, R-14): no `MERGE`, no `UNIQUE NULLS NOT DISTINCT`, no SQL/JSON
  constructors, no `GRANT … SET`, no PG 15+ functions. The local image is PostgreSQL 14, so the optional integration
  test catches most mistakes.
- No transaction control (`BEGIN`, `COMMIT`, `ROLLBACK`) and no statements that cannot run in a transaction
  (`CREATE INDEX CONCURRENTLY`, `VACUUM`, `CREATE DATABASE`): the runner wraps each file in one transaction.
  On the small learning tables a plain `CREATE INDEX` is fine.
- No data values from users in a migration (personal data stays out of Git); no secrets, no `GRANT` of passwords.
- Column lists live in spec 06 §Outputs (or the spec of the feature that adds them); a migration that changes a table
  updates that spec first.
- **Never edit an applied file** — its SHA-256 is stored; the next run stops with `MIGRATION_CHECKSUM_MISMATCH: V<n>`.
  **Fix forward:** add `V<n+1>__fix_….sql`. No down-migrations. A file that was never applied anywhere (not in the
  `status` output as applied) may still be edited.

## Runner rules (as implemented)

0. The sync dispatcher sends an event to the runner only if it has a top-level `action` key whose value is not one
   of the vector actions `embed-missing`, `seed`, `similar` (those go to `vectors.handle`, bedrock-embeddings skill;
   every other value, including unknown ones, still reaches the runner → `MIGRATION_BAD_REQUEST`); an EventBridge
   `UserConfirmed` envelope goes to the upsert `user_sync.handle` (user-sync skill), anything else ends as
   `UNSUPPORTED_EVENT` (no DB connection).
1. Event must be exactly `{"action":"migrate"}` or `{"action":"status"}`, else `MIGRATION_BAD_REQUEST` (no DB
   connection).
2. Connect via `db.connect(timeout=55)` (IAM token, TLS; socket timeout per read, below the 60 s sync function timeout); `CREATE TABLE IF NOT EXISTS schema_migrations` (the runner owns this
   table, no migration creates it).
3. Validate files (name, versions 1..n; the reported file is the first offending one in version order — for a gap
   the file after the gap, for a duplicate the second name), then the checksum of every applied version; an applied
   version whose file is gone also counts as `MIGRATION_CHECKSUM_MISMATCH`. Nothing is applied on any of these errors.
4. `status` returns current/pending and applies nothing.
5. `migrate`: per pending file, ascending: `BEGIN` → `pg_try_advisory_xact_lock(7302170601)` (false →
   `MIGRATION_LOCKED`) → re-check the version is still unapplied (a parallel run may have applied it: skipped, not
   in `applied`) → `execute_simple(file)` → insert `schema_migrations` row → `COMMIT`. SQL error →
   `ROLLBACK`, `MIGRATION_FAILED: V<n> <SQLSTATE>`; earlier files of the run stay committed. Lost connection or
   socket timeout inside the file's transaction (pg8000 `InterfaceError`, raw `OSError`) has no SQLSTATE →
   `MIGRATION_FAILED: V<n> UNKNOWN` (`errorClass` names the cause); run `status` to see whether `V<n>` committed.
6. Connection closed in `finally`; one JSON log line with `action`, `applied`, `current`, `outcome`, `errorClass`.

## How the owner runs it (runbook building blocks for devops)

1. Build `py -3.13 lambdas/package.py sync` → `build/lambdas/sync.zip` (agent), owner uploads it to
   `aws-challenge-sync` (Lambda console → Code → *Upload from* → *.zip file*). Uploading applies nothing: every sync
   zip carries the migration files, a new file stays pending until the owner invokes `migrate`. Do not edit an
   applied file in a later sync release (checksum).
2. `aws-challenge-sync` → Test tab → event JSON `{"action":"status"}` → check `pending`; then `{"action":"migrate"}`
   → result `{"applied":[…],"current":n}`; repeat `status` → `pending: []`. Never use the console's default template
   (`UNSUPPORTED_EVENT`).
3. Evidence: the Test-tab result and the log line in `/aws/lambda/aws-challenge-sync`.
4. On `MIGRATION_FAILED`: the failing file was rolled back; fix forward or fix the never-applied file, rebuild,
   re-upload, re-run. On `MIGRATION_LOCKED`: another run is active — wait and re-run. On `DB_CONNECT_FAILED`: check
   the proxy IAM auth setting, the role's `rds-db:connect`, env vars (spec 06 edge cases).

## Local check

`docker compose up -d` (PostgreSQL 14 + pgvector), then set `MIGRATE_TEST_DATABASE_URL=postgresql://app:app@localhost:5432/aws_challenge`
and run `pytest lambdas/shared lambdas/sync`: the integration test applies all files in a throw-away schema
(search path `<schema>, public`, so an extension already installed in `public` is found; a newly created one lives in
the schema and is dropped with it), checks `users` against spec 06 (columns, types incl. `vector(1024)`, nullability,
defaults, primary key + HNSW index only) and drops the schema.
