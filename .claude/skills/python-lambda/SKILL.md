---
name: python-lambda
description: How this project writes, tests and packages its Python 3.12 Lambda functions in lambdas/ (local tests on 3.13, code kept 3.12-compatible) — directory layout, local set-up on Windows, pytest command, zip packaging (build/lambdas/<function>.zip with the shared DB helper and pinned pure-Python requirements), the shared DB helper (IAM auth token + verified TLS to RDS Proxy, one connection per invocation), the one-JSON-line log and how to add a function. Use when creating or changing any code under lambdas/, building a zip for an owner upload, or reviewing a backend task.
license: MIT
metadata:
  domain: backend
  triggers: Lambda, Python, lambdas/, lambda_handler, pytest, zip, package.py, requirements.txt, pg8000, RDS Proxy, IAM auth, generate_db_auth_token, db.py, DB_CONNECT_FAILED, log line
  role: specialist
  scope: implementation
  related-skills: postgres-migrations, postgres-pro, test-master
  source: project (created by T03-02)
  used-by: [backend, tester, devops]
---

# Python Lambda functions

Decisions: ADR-015 revised (Python 3.12 Lambdas, zip deploys; functions `admin`, `chatbot`, `sync` + trigger
`post-confirmation` — no other function), ADR-006 revised (IAM auth to RDS Proxy), ADR-017 revised (migration runner
inside `sync`), design
[user-sync](../../../docs/design/user-sync.md) §1, §4, §5. Contract of the DB access: [spec 06](../../../docs/specs/06-users-table-and-migrations.md).
Deployed names and settings: [ENVIRONMENT.md](../../../docs/ENVIRONMENT.md) — link, never copy. Agents build the zip;
the owner uploads it (CLAUDE.md §3.11; Lambda console → *Upload from .zip file*, no console code edits afterwards).

## Layout

Function-specific rules live in their own skills: `admin-api` (lambdas/admin), `user-sync` (sync upsert, trigger), `postgres-migrations` (sync migrations), `bedrock-embeddings` (sync embeddings and vector actions).

```
lambdas/
  package.py               zip builder (below)
  requirements-dev.txt     local test tools (pytest, boto3) — never packaged
  shared/db.py             DB helper, copied into every zip; tests in shared/tests/
  <function>/
    lambda_function.py     handler lambda_function.lambda_handler(event, context)
    requirements.txt       runtime deps, every transitive dep pinned (==), pure Python only; omit if none
    <data>/                packaged data, e.g. sync/migrations/
    tests/conftest.py      puts lambdas/<function> and lambdas/shared on sys.path (same layout as the zip)
    tests/test_*.py        pytest; test doubles for boto3 and the DB
  sync/                    lambda_function.py = dispatcher (spec 06 §Inputs: `action` embed-missing/seed/similar →
                           vectors.handle, other `action` → migrator.handle, UserConfirmed → user_sync.handle, else
                           UNSUPPORTED_EVENT); migrator.py = migration runner; migrations/V<n>__*.sql
                           (postgres-migrations skill); user_sync.py = upsert (user-sync skill); embeddings.py = Bedrock
                           Titan V2 client + text template, vectors.py = vector actions (bedrock-embeddings skill)
  post-confirmation/       Cognito trigger, boto3 only (no requirements.txt), outside the VPC (user-sync skill)
```

In the zip every file sits at the root: `lambda_function.py`, `db.py`, data directories, installed packages. So code
imports the helper as `import db`. A module or directory in a function must not be named like a file in `shared/` or
like an installed requirement (file or package; the packager stops on a clash). `boto3` comes from the Lambda runtime and is **never** listed in `requirements.txt`.

## Python version: runtime 3.12, local 3.13

- Every function runs on the Lambda **Python 3.12** runtime (ADR-015 revised 2026-11-16); never change a function's
  runtime in a runbook.
- The owner's machine has only 3.13 and 3.8 in the `py` launcher, so tests and packaging run on **3.13**. Code must
  therefore stay **3.12-compatible**: no API or syntax added in 3.13 (e.g. `copy.replace`, `warnings.deprecated`,
  `typing.ReadOnly`, `typing.TypeIs`, type-parameter defaults `[T = int]`, `pathlib.Path.from_uri`,
  `os.process_cpu_count`, `base64.z85encode`); when unsure, check "New in version 3.13" in the Python docs. A backend
  review states the 3.12 check as "static check only".
- Every pinned package in a `requirements.txt` must support Python 3.12 (`Requires-Python` and a `py3-none-any`
  wheel); `package.py` installs with `--python-version 3.12`, so a pin without 3.12 support fails the build.

## Local set-up (Windows; `python` opens the MS Store on the owner's machine — always `py -3.13`)

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r lambdas/requirements-dev.txt -r lambdas/sync/requirements.txt
```

Install the `requirements.txt` of every function you test. Keep `.venv/`, `__pycache__/` and `.pytest_cache/`
out of Git.

## Tests

```powershell
.venv\Scripts\python -m pytest lambdas/shared lambdas/<function>
```

One pytest session per function (every function has a module called `lambda_function`). The packager has its own
tests: `.venv\Scripts\python -m pytest lambdas/tests` (stubbed pip, no network). Rules: AWS clients and the
DB connection are replaced by test doubles (monkeypatch `db.connect`, `db._rds_client`, `pg8000.native.Connection`);
no test reaches AWS. Optional integration tests are skipped unless their env var is set — migration runner in
`sync`: `MIGRATE_TEST_DATABASE_URL=postgresql://app:app@localhost:5432/aws_challenge` with `docker compose up -d`
(local PostgreSQL 14 + pgvector, R-14).

## Packaging

```powershell
.venv\Scripts\python lambdas/package.py <function>     # -> build/lambdas/<function>.zip (build/ is git-ignored)
```

The script installs `requirements.txt` with `pip --target --no-deps --only-binary=:all: --python-version 3.12` (so the pins must list
every transitive dependency), fails if any `.pyd`/`.so` appears (a zip built on Windows must be pure Python), copies
the function directory without `tests/`, `__pycache__`, `requirements.txt`, `conftest.py`, adds `lambdas/shared/*.py`
and writes a zip with fixed timestamps (same sources → same SHA-256; give the hash to the owner with the zip).
Needs PyPI access, not AWS.

## DB helper `shared/db.py`

- `db.connect()` → `pg8000.native.Connection` to `DB_PROXY_ENDPOINT:5432`, database `DB_NAME`, user `DB_USER`
  (env var names exactly as spec 06 §Inputs), password = IAM auth token from
  `boto3.client("rds").generate_db_auth_token(...)` (local SigV4 signature, no network call, valid 15 min, never
  logged), TLS context `ssl.create_default_context()` with `CERT_REQUIRED` + host name check; socket timeout 10 s by default — it applies to connect and to **every**
  later read, so a code path with long statements passes its own (migration runner in `sync`:
  `db.connect(timeout=55)`, below the 60 s sync function timeout; the upsert path keeps the 10 s default).
  No password, secret or connection string from configuration; no `DB_SECRET_ARN`.
- Any failure (missing env var, token, network, TLS, auth) → `db.DbConnectError`, message `DB_CONNECT_FAILED`,
  original exception as `__cause__` (log only its class name as `errorClass`). No password fallback, never plain text.
- The RDS client is created lazily once per execution environment (`db._rds()`); nothing connects at import.
- One connection per invocation: open lazily on first DB use, close in `finally` with `db.close_quietly(conn)`.
- `pg8000.native`: `conn.run(sql, **params)` with `:name` placeholders — parameterised SQL only, never string
  formatting of values; transactions explicit (`run("BEGIN")` … `run("COMMIT")`, autocommit otherwise);
  `conn.execute_simple(sql)` runs a multi-statement script (simple-query protocol, no parameters) — migrations only.
  Errors: `pg8000.native.DatabaseError(dict)`, SQLSTATE in `args[0]["C"]`.
- Re-check when first deployed (T03-03): RDS Proxy presents an ACM (Amazon Trust Services) certificate that the
  runtime's default trust store accepts; if not, ship the Amazon root CA PEM in the zip and load it into the context.

## Log line

Until Week 6 (Powertools, ADR-012): exactly one JSON line per invocation, printed to stdout from a `finally` block —
`level`, `message`, `function` (`context.function_name`), `awsRequestId` (`context.aws_request_id`), `userSub` where
known, `outcome`, `durationMs`, `errorClass` on failure, plus the fields the function's spec lists. `message` is a
fixed text or one of the function's own error codes; never `str()` of a foreign exception (may contain SQL values),
never tokens, passwords, e-mail, names or any attribute value (field names only). Example: `lambdas/sync/migrator.py`.

## Adding a function

1. `lambdas/<function>/lambda_function.py` with `lambda_handler`; module-level constants and clients only, no
   network call or DB connection at init.
2. `requirements.txt` with all transitive deps pinned (check with `pip install` into a scratch venv + `pip freeze`;
   wheels must be `py3-none-any`).
3. `tests/conftest.py` (copy from `lambdas/sync/tests/`) and tests with doubles; run pytest as above.
4. Row in `lambdas/README.md`; build the zip; the devops runbook of the deploy task tells the owner what to upload.
