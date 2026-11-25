---
name: user-sync
description: How this project copies confirmed Cognito users into PostgreSQL — the Cognito PostConfirmation trigger aws-challenge-post-confirmation (outside the VPC, one EventBridge PutEvents, never fails a confirmation), the custom bus aws-challenge-events, the rule aws-challenge-user-confirmed, and the UserConfirmed upsert in aws-challenge-sync (validation, tolerant mapping, idempotent upsert, log line, errors), plus the re-sync / back-fill runbook outline with a sample event and how to test locally. Use when changing lambdas/post-confirmation or lambdas/sync/user_sync.py, writing the runbook that deploys or wires the chain, re-syncing a user, or reviewing evidence for spec 07.
license: MIT
metadata:
  domain: backend
  triggers: user sync, UserConfirmed, embedding on upsert, PostConfirmation, post-confirmation, PutEvents, EventBridge, aws-challenge-events, aws-challenge-user-confirmed, user_sync.py, upsert, publish_failed, rejected, invalidFields, re-sync, back-fill, Send events
  role: specialist
  scope: implementation
  related-skills: python-lambda, postgres-migrations, bedrock-embeddings, cognito-user-pool, postgres-pro
  source: project (created by T03-04)
  used-by: [backend, devops, tester]
---

# User sync: Cognito → EventBridge → Sync Lambda → PostgreSQL

Decisions: ADR-016 (Q-17 A), ADR-006 revised (IAM auth to RDS Proxy), ADR-017 revised (dispatch in `sync`); design
[user-sync](../../../docs/design/user-sync.md) §3, §4. Contract — event fields, mapping, outcomes, log fields, edge
cases: [spec 07](../../../docs/specs/07-user-sync.md) (single home; link, never copy). Dispatch table and `users`
columns: [spec 06](../../../docs/specs/06-users-table-and-migrations.md). Deployed names and settings:
[ENVIRONMENT.md](../../../docs/ENVIRONMENT.md). Code conventions, tests and packaging:
[python-lambda](../python-lambda/SKILL.md).

```
Owner: Cognito console "Confirm account" (AdminConfirmSignUp)
  -> PostConfirmation trigger  lambdas/post-confirmation/lambda_function.py   (no VPC, 5 s Cognito limit)
  -> PutEvents (1 entry)       bus from env EVENT_BUS_NAME, source aws-challenge.cognito, detail-type UserConfirmed
  -> rule (pattern on source + detail-type) -> async invoke of aws-challenge-sync
  -> lambdas/sync/lambda_function.py dispatch -> user_sync.handle
       -> Bedrock Titan V2 embedding of the profile text (before the DB connection; never raises)
       -> one upsert into users (incl. embedding) via RDS Proxy
```

## Trigger rules (`lambdas/post-confirmation/`)

- Dependencies: only `boto3`/`botocore` from the Lambda runtime → no `requirements.txt`. (The packager still adds
  `shared/db.py` to the zip; the trigger never imports it.)
- Env: `EVENT_BUS_NAME` only. Read inside the handler; a missing value is a `publish_failed` (`errorClass`
  `KeyError`), never an init error.
- Only `triggerSource == PostConfirmation_ConfirmSignUp` publishes; anything else (`…_ConfirmForgotPassword`,
  malformed event) → `ignored`, no call.
- Detail = `version` 1, `userPoolId`, `sub`, `email`, `attributes` (allow-list `ALLOWED_ATTRIBUTES` — raw string
  values, missing keys left out; never `email_verified`, `cognito:*` or other custom attributes), `confirmedAt` (UTC,
  milliseconds, `Z`). Adding an attribute = spec 07 §Inputs first, then the allow-list and the sync mapping.
- **Never raises, always returns the Cognito event object unchanged** — a raised error or a Lambda timeout would make
  the owner's confirmation fail (R-02). `put_events` exception or `FailedEntryCount > 0` → `publish_failed` with
  `errorClass` = exception class or the entry's `ErrorCode`.
- EventBridge client created lazily once per environment with `connect_timeout=1`, `read_timeout=2`, standard
  retries, `total_max_attempts=1` (no retry) — worst case ~3 s plus start-up, inside the 5 s Cognito wait and the
  5 s function timeout (ARCH review B1, 2026-11-16); a missed event is re-sent by the re-sync runbook.
- Log: one JSON line (fields spec 07 §Outputs); `userSub` is the Cognito `sub`; no attribute value.

## Sync rules (`lambdas/sync/user_sync.py`, route in `lambda_function.py`)

- Route: after the `action` check (a top-level `action` always goes to the migration runner), before the
  `UNSUPPORTED_EVENT` fallback: `source == aws-challenge.cognito` and `detail-type == UserConfirmed`
  (`user_sync.is_user_confirmed`). Changing it changes spec 06 §Inputs first.
- Validation (no DB call on failure, returns `{"outcome":"rejected"}`, no exception — a retry cannot fix it):
  `detail.sub` canonical UUID (8-4-4-4-12 hex, stored lower-case), else `invalidFields ["sub"]`; `detail.email`
  string, trimmed + lower-cased, non-empty, else `["email"]` (`userSub` logged when the `sub` was valid).
- Mapping (spec 07 §Outputs): missing or `""` → NULL without a log entry; a present but unusable value → NULL and its
  event field name in `invalidFields` (`birthdate`, `custom:height`, `custom:weight`, `confirmedAt`, a non-string
  text attribute, `attributes` when it is not an object). Digits are ASCII only (`[0-9]`); integers outside the SPA
  range are stored if they fit PostgreSQL `integer`; `confirmedAt` without offset is taken as UTC. Unknown keys are
  ignored.
- Embedding (Week 4, spec 10; details: bedrock-embeddings skill): after mapping, `embeddings.build_text(params)` →
  no text → `skipped` (no call); else one `InvokeModel` **before** `db.connect()`. Any Bedrock failure → `embedding`
  NULL, log `embedding: failed` + `errorClass`, **normal return** (no raise, no async retry — ADR-020). The upsert
  writes `embedding = EXCLUDED.embedding` on conflict too, so a failed re-sync clears a stale vector;
  `{"action":"embed-missing"}` refills NULLs. Log adds `embedding` and `bedrockMs` (not on `rejected`).
- One statement `SQL_UPSERT`: `INSERT … ON CONFLICT (id) DO UPDATE` of every mapped column (incl. `embedding` as
  `CAST(:embedding AS vector)`) + `updated_at = now()`,
  `created_at` untouched, explicit `CAST(:param AS <type>)`, `RETURNING (xmax = 0)` → `inserted` / `updated`. Values
  only as pg8000 `:name` parameters. No explicit transaction (single statement, autocommit).
- Connection: `db.connect()` with the shared 10 s socket timeout (not the runner's 55 s), closed in `finally`.
- Errors: `db.DbConnectError` (`DB_CONNECT_FAILED`) is re-raised; a pg8000 `DatabaseError` / `InterfaceError` or an
  `OSError` becomes `UserSyncError("USER_SYNC_FAILED: <SQLSTATE|UNKNOWN>")` (original as `__cause__`, so no foreign
  text with values reaches the function error); anything else is re-raised and logged as `unexpected error`. All of
  them make Lambda retry the async invocation; after the retries the row is missing until a re-sync.
- Log: one JSON line, `level` INFO (`inserted`/`updated`), WARNING (`rejected`), ERROR (`failure`).

## Re-sync / back-fill runbook outline (for devops; owner executes, CLAUDE.md §3.11)

Use for a user confirmed before the trigger existed, after `publish_failed`, or after a sync `failure`.

1. Cognito console → User pool (ENVIRONMENT.md) → Users → the user → copy `sub`, `email` and the seven registration
   attributes that are set.
2. EventBridge console → *Event buses* → `aws-challenge-events` → *Send events*: Event source
   `aws-challenge.cognito`, Detail type `UserConfirmed`, Event detail = the JSON below with the copied values (leave
   out attributes that are not set; never `email_verified`).
3. Verify: `/aws/lambda/aws-challenge-sync` shows one line with that `userSub` and `outcome` `inserted` (new) or
   `updated` (existing); `rejected` means `sub`/`email` was mistyped (`invalidFields` names it). `embedding` is
   `stored` only while the Bedrock endpoint exists (ADR-020); `failed` / `UNREACHABLE` otherwise — then run
   `{"action":"embed-missing"}` in the next session.

Sample event detail (fictitious values; the pool id is a placeholder — take the real one from ENVIRONMENT.md):

```json
{
  "version": 1,
  "userPoolId": "eu-west-1_EXAMPLE",
  "sub": "8f1c2a3b-0000-4000-8000-000000000001",
  "email": "test.user@example.com",
  "attributes": {
    "given_name": "Test",
    "family_name": "User",
    "gender": "female",
    "birthdate": "1990-05-17",
    "custom:country": "Austria",
    "custom:height": "170",
    "custom:weight": "62"
  },
  "confirmedAt": "2026-11-16T10:00:00.000Z"
}
```

Sending it twice gives `inserted` then `updated` and still one row (AC-07.5). For a direct sync Test-tab check use the
full envelope (`"source"`, `"detail-type"`, `"detail"` at the top level) — never a payload with a top-level `action`.

## Testing locally

```powershell
.venv\Scripts\python -m pytest lambdas/shared lambdas/sync          # dispatch, runner, upsert (test_user_sync.py)
.venv\Scripts\python -m pytest lambdas/post-confirmation            # trigger (StubEvents for the boto3 client)
```

Doubles: the trigger tests replace `lambda_function._events_client` with a stub recording `put_events`; the sync
tests replace `db.connect` with a fake connection that keeps `users` as a dict and answers `[[inserted]]`, and
`embeddings._bedrock_client` with `tests/bedrock_stub.StubBedrock` (autouse; no test reaches Bedrock).
`test_user_sync_integration.py` runs the real upsert against local PostgreSQL 14 after applying the migrations in a
throw-away schema — skipped unless `MIGRATE_TEST_DATABASE_URL` is set (`docker compose up -d`, python-lambda skill).
Build: `py -3.13 lambdas/package.py post-confirmation` and `… sync`.
