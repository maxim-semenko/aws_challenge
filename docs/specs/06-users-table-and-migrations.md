# Spec 06 — Users table, migrations and database access

Requirements: [week-03](../requirements/week-03-rest-api-data.md) W3-G1, W3-G5, S1, S5 ·
Design: [user-sync](../design/user-sync.md) §1, §2, §5
Tasks: T03-02, T03-03 (AC-06.6 for `sync`), T03-07 (AC-06.6 for `admin`), T03-10

Written against [Q-16](../RISKS.md#q-16) option A and [Q-18](../RISKS.md#q-18) option A — both accepted by the
owner on 2026-11-13 (ADR-017, ADR-006 revised). **Revised 2026-11-16 (owner):** no function `aws-challenge-migrate`;
the runner is a module of `aws-challenge-sync` (ADR-017 revised, Q-16 amended); runtime Python 3.12 (ADR-015
revised). Runner rules, results, error strings and tables are unchanged; AC-06.1, AC-06.2, AC-06.4, AC-06.5, AC-06.6
reworded.

## Purpose

The database schema is created only by versioned SQL migrations applied by the migration runner of the function
`aws-challenge-sync` inside the VPC, on the owner's direct invoke, and every VPC function connects to PostgreSQL only
through RDS Proxy with IAM authentication over TLS, without any secret in its code or configuration. The first
migration creates the `users` table that the sync chain (spec 07) writes and the Admin API (spec 08) reads.

## Inputs

**Migration files** — `lambdas/sync/migrations/V<n>__<description>.sql`; `<n>` integer ≥ 1 without leading zeros,
`<description>` matches `[a-z0-9_]+`; UTF-8; PostgreSQL 14 syntax.

**Event dispatch of `aws-challenge-sync`** (single home of the routing rule), checked in this order, before any DB
connection:

| Event | Route |
|---|---|
| a JSON object with a top-level key `action` | migration runner (below) |
| `source` = `aws-challenge.cognito` and `detail-type` = `UserConfirmed` | user upsert ([spec 07](07-user-sync.md)) |
| anything else | function error `UNSUPPORTED_EVENT` (see Outputs) |

**Direct invoke of `aws-challenge-sync` for migrations** (console Test tab, owner):

| Field | Type | Valid range | Required |
|---|---|---|---|
| `action` | string | `migrate` or `status` | yes |

Any other field or value → error `MIGRATION_BAD_REQUEST` (see Outputs).

**Configuration of each VPC function that uses the database** (`admin`, `sync`) — environment variables,
names exact, values in [ENVIRONMENT.md](../ENVIRONMENT.md):

| Name | Valid range | Required |
|---|---|---|
| `DB_PROXY_ENDPOINT` | host name of the RDS Proxy default endpoint | yes |
| `DB_NAME` | database name as built | yes |
| `DB_USER` | the DB user registered with the proxy | yes |

No `DB_SECRET_ARN`, password or connection string with credentials. Port fixed 5432; region from the Lambda runtime
(`AWS_REGION`).

## Outputs

**Table `users`** (created by `V1__create_users.sql`; single home of the column list):

| Column | Type | Null | Default | Source (Cognito attribute) |
|---|---|---|---|---|
| `id` | `uuid` | no, **primary key** | — | `sub` |
| `email` | `text` | no | — | `email` (stored lower-case) |
| `given_name` | `text` | yes | — | `given_name` |
| `family_name` | `text` | yes | — | `family_name` |
| `gender` | `text` | yes | — | `gender` |
| `birthdate` | `date` | yes | — | `birthdate` (`YYYY-MM-DD`) |
| `country` | `text` | yes | — | `custom:country` |
| `height_cm` | `integer` | yes | — | `custom:height` |
| `weight_kg` | `integer` | yes | — | `custom:weight` |
| `confirmed_at` | `timestamptz` | yes | — | event `confirmedAt` |
| `created_at` | `timestamptz` | no | `now()` | set on insert only |
| `updated_at` | `timestamptz` | no | `now()` | set on every upsert |

No CHECK constraint on registration values, no unique constraint on `email`, no other index, no `embedding` column
(Week 4, Q-15).

**Table `schema_migrations`**: `version integer PRIMARY KEY`, `description text NOT NULL`, `checksum text NOT NULL`
(lower-case hex SHA-256 of the file bytes), `applied_at timestamptz NOT NULL DEFAULT now()`. Created by the runner if
missing (not by a migration).

**Result of a migration invoke of `aws-challenge-sync`**:

| Case | Return value / error |
|---|---|
| `migrate`, success | `{"applied": [<versions applied now>], "current": <highest applied version>}` (`applied` empty when nothing was pending) |
| `status` | `{"current": <highest applied version or 0>, "pending": [<versions not applied>]}`; changes nothing |
| bad request | function error, message `MIGRATION_BAD_REQUEST` |
| file name invalid, version gap or duplicate | function error `MIGRATION_INVALID_FILES: <file name>`; nothing applied |
| checksum of an applied version differs | function error `MIGRATION_CHECKSUM_MISMATCH: V<n>`; nothing applied |
| another run holds the lock | function error `MIGRATION_LOCKED`; nothing applied |
| SQL error in `V<n>` | function error `MIGRATION_FAILED: V<n> <SQLSTATE>`; `V<n>` rolled back, earlier files of this run stay applied |
| DB connection fails | function error `DB_CONNECT_FAILED` |
| event matches no route of the dispatch table | function error `UNSUPPORTED_EVENT`; no DB connection |

**Log line** of a migration invoke (one per invocation, JSON): `level`, `message`, `function`, `awsRequestId`,
`action`, `applied`, `current`, `outcome` (`success` / `failure`), `durationMs`, `errorClass` (on failure). Never SQL
text with values, the auth token or a password. An `UNSUPPORTED_EVENT` invocation logs one line with `level`
`ERROR`, `message` `UNSUPPORTED_EVENT`, `function`, `awsRequestId`, `outcome` `failure`, `durationMs` — never the
event content.

## Behaviour

1. The sync handler routes the event (dispatch table). For a migration invoke the runner validates the event,
   generates an IAM auth token for `DB_USER` at `DB_PROXY_ENDPOINT:5432` locally (no network call) and opens one TLS
   connection (certificate verified) to the proxy.
2. It creates `schema_migrations` if missing, lists the packaged files, validates names, versions (1..n, no gap, no
   duplicate) and the checksums of applied versions.
3. `status`: returns current and pending versions.
4. `migrate`: for each pending version in ascending order, in one transaction: take `pg_try_advisory_xact_lock(<fixed
   key>)` (not acquired → `MIGRATION_LOCKED`), run the file, insert its `schema_migrations` row, commit.
5. The connection is closed in all cases; one log line is written.
6. `admin` and `sync` connect the same way (shared helper); a connection is opened lazily on first DB use in an
   invocation and closed at its end.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| Second `migrate` run with nothing pending | `{"applied": [], "current": 1}`; no change |
| An applied file was edited | `MIGRATION_CHECKSUM_MISMATCH`; fix forward with a new version |
| Two runs at once | one applies, the other gets `MIGRATION_LOCKED` or finds nothing pending |
| Proxy still accepts only passwords (IAM auth not enabled) | `DB_CONNECT_FAILED`, log `errorClass` set; no password fallback |
| Role lacks `rds-db:connect` | `DB_CONNECT_FAILED` |
| TLS cannot be established | `DB_CONNECT_FAILED`; never plain text |
| Local PostgreSQL 17 vs RDS 14 | the SQL uses only PostgreSQL 14 features; the local image is PostgreSQL 14 (R-14) |
| A sync zip with a new migration file is uploaded | nothing is applied until the owner invokes `{"action":"migrate"}`; `status` lists it as pending |
| EventBridge `UserConfirmed` event | never reaches the runner (no top-level `action`) |
| Test event `{}` or the console's default template | `UNSUPPORTED_EVENT`, no DB connection |

## Acceptance Criteria

AWS-side criteria are verified from evidence the owner provides (console screenshots, Test-tab outputs); agents have
no AWS access (CLAUDE.md §3.11). AC-06.1 and AC-06.2 are verified locally.

- [ ] AC-06.1 `lambdas/sync/migrations/V1__create_users.sql` creates `users` exactly as in §Outputs (column names,
  types, nullability, defaults, primary key; no other constraint or index) — checked by reading the file and by the
  optional local run against PostgreSQL 14
- [ ] AC-06.2 `pytest` for `lambdas/sync` passes and covers: pending files applied in order in one transaction
  each with their `schema_migrations` row; nothing pending → `applied: []`; version gap, duplicate, bad name →
  `MIGRATION_INVALID_FILES` with nothing applied; checksum mismatch; lock not acquired; SQL error rolls back only the
  failing file; bad request; connection uses the IAM token with TLS and never a password from configuration;
  dispatch: an `action` event reaches the runner, a `UserConfirmed` envelope never does, any other event →
  `UNSUPPORTED_EVENT` without a DB connection and with the log line of §Outputs
- [ ] AC-06.3 RDS Proxy shows IAM authentication **required** for the registered DB user and Require TLS enabled
  (owner screenshot)
- [ ] AC-06.4 `aws-challenge-sync` is in the private subnets with the Lambda security groups as built
  ([ENVIRONMENT.md](../ENVIRONMENT.md) §Compute; there is no `sg-lambda`), runtime Python 3.12, timeout 60 s, env vars
  exactly `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_USER`, code = the zip built from Git (`lambdas/sync`, SHA-256 as given
  by the agent); its role allows only `rds-db:connect` on the proxy `dbuser` ARN plus VPC access and logging (owner
  screenshots; account id masked)
- [ ] AC-06.5 Test-tab invoke of `aws-challenge-sync` with `{"action":"migrate"}` returns
  `{"applied":[1],"current":1}`; a second invoke returns `{"applied":[],"current":1}`; `{"action":"status"}` returns
  `{"current":1,"pending":[]}`; the log line of each run is in `/aws/lambda/aws-challenge-sync`
- [ ] AC-06.6 No function configuration of `admin`, `sync` contains `DB_SECRET_ARN`, a password or a
  connection string with credentials, and none of their roles has `secretsmanager:GetSecretValue` (owner
  screenshots); `git grep` finds no secret in `lambdas/`
