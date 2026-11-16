---
id: T03-02
title: "Python Lambda base (layout, packaging, DB helper) and migrations runner in sync with V1 users table"
phase: P3-rest-api-data
status: Done
agent: backend
skills: [postgres-pro, test-master]
depends_on: []
blocked_by: []
design: ../../design/user-sync.md
spec: ../../specs/06-users-table-and-migrations.md
acceptance: [AC-06.1, AC-06.2]
---
# T03-02 — Python Lambda base and migrations runner in sync with V1 users table

## // BUSINESS CONTEXT

W3-G1, S1, S5: the users table is the meeting point of the sync chain and the Admin API, and the first Python code
in Git sets the conventions every later function follows (ADR-015, R-15). This task produces the code; the owner
deploys it in T03-03 (to `aws-challenge-sync`, which hosts the runner — ADR-017 revised 2026-11-16).

## // TECHNICAL CONSTRAINTS

- Runtime Python **3.12** (ADR-015 revised 2026-11-16); local tests and packaging on Python 3.13, so no 3.13-only
  API, and every pinned package must support 3.12 (python-lambda skill). One directory per function; pinned
  pure-Python `requirements.txt` (`pg8000` and its dependencies); `boto3` from the runtime (not packaged); handler
  `lambda_function.lambda_handler`; no network call or DB connection at init (CLAUDE.md §7).
- No function `migrate`: the runner is the module `lambdas/sync/migrator.py`, reached through the dispatch of
  `lambdas/sync/lambda_function.py` exactly as spec 06 §Inputs (dispatch table) and §Outputs (`UNSUPPORTED_EVENT`).
  The `UserConfirmed` branch (upsert) is T03-04; until then such an event takes the "anything else" route.
- DB helper `lambdas/shared/db.py`: IAM auth token via `boto3` `generate_db_auth_token` (no network call), TLS with
  certificate verification, env vars exactly as spec 06 §Inputs, one connection per invocation, no password from
  configuration. Copied into each zip by the packaging script (design user-sync §5).
- Migration runner and `V1__create_users.sql` exactly per spec 06 (§Outputs table is the single home of the columns);
  PostgreSQL 14 syntax only (R-14).
- Parameterised SQL only; pytest with test doubles for `boto3` and the DB connection; an optional integration test
  against local PostgreSQL 14 is skipped unless an env var with a local connection URL is set.
- Packaging works on Windows (zip of pure-Python files runs on Lambda).

## // SCOPE

**Implement**
- `lambdas/shared/db.py`; packaging script that builds `build/lambdas/<function>.zip` (function files + shared
  helper + installed requirements, no tests)
- `lambdas/sync/` (dispatcher `lambda_function.py`, runner `migrator.py`, `migrations/V1__create_users.sql`,
  `requirements.txt`, `tests/`) — moved from the former `lambdas/migrate/` (rework 2026-11-16, Notes)
- `docker-compose.yml`: PostgreSQL 14 image with pgvector (re-check the image tag) for the optional test (R-14)
- Skill `python-lambda` (layout, packaging command, pytest command, DB helper, logging line, how to add a function)
  and skill `postgres-migrations` (naming, runner rules, how the owner runs it, fix-forward); skills ownership rule
- Update `lambdas/README.md` (new directories)

**Exclude**
- The `UserConfirmed` upsert in `sync`, `post-confirmation`, `admin` handlers (T03-04, T03-06); any AWS change
  (T03-03); `embedding` column (Week 4)

**Interfaces that must match**
- Column list and runner results/errors: spec 06 character for character; env var names: spec 06 §Inputs.

## Definition of Done

- [ ] pytest green (AC-06.2, incl. dispatch); zip builds for `sync`; AC-06.1 checked (local run if the optional test
  ran) — done for the former `migrate` layout, to be redone after the 2026-11-16 rework
- [ ] Skills `python-lambda`, `postgres-migrations` added (done; re-worded by ARCH 2026-11-16 for the sync layout —
  backend checks them against the code); ARCH re-review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning. `Blocked` until Q-16 (runner location) and Q-18 (IAM auth vs secret) are
  answered; the scope above follows the recommended options. Needs the owner's CLAUDE.md edit for §9 ("major 17" →
  14) — agents do not edit CLAUDE.md.
- 2026-11-13: Q-16 A and Q-18 A accepted by the owner (ADR-017, ADR-006 revised); design user-sync `Accepted` →
  `Todo`, start gate holds; scope unchanged. CLAUDE.md §9 now says local major 14 (owner-approved edit); the
  `docker-compose.yml` image switch from `pgvector/pgvector:pg17` stays in this task's scope. No Q-18 owner facts are
  needed here (env var names are fixed by spec 06; values come with T03-03).
- 2026-11-16 (backend): implemented; status `Review` (architect review pending; PLAN.md row not edited by backend —
  to be synced). Files: `lambdas/shared/db.py` (+ `shared/tests/`), `lambdas/migrate/` (`lambda_function.py`,
  `migrations/V1__create_users.sql`, `requirements.txt` — pg8000 1.31.6, scramp 1.5.0, asn1crypto 1.5.1,
  python-dateutil 2.9.0.post0, six 1.17.0, all `py3-none-any` wheels — `tests/`), `lambdas/package.py`,
  `lambdas/requirements-dev.txt` (pytest 9.2.0, boto3 1.44.3; test only), `lambdas/README.md`,
  `docker-compose.yml` (`pgvector/pgvector:0.8.7-pg14`, tag checked on Docker Hub 2026-11-16; volume renamed
  `pgdata14` because a PG 17 data directory cannot be opened by 14), skills `python-lambda`, `postgres-migrations`.
  Evidence (Python 3.13.2, scratch venv outside the repo):
  - `pytest lambdas/shared lambdas/migrate`: **53 passed, 1 skipped** (the optional integration test,
    `MIGRATE_TEST_DATABASE_URL` not set); each module alone also green (migrate 40 passed + 1 skipped, shared 13).
  - AC-06.2: covered by `lambdas/migrate/tests/test_migrate.py` (order + one transaction with history row each,
    nothing pending, status, bad names / gap / missing V1 / duplicate / non-UTF-8 → `MIGRATION_INVALID_FILES` with
    nothing applied, checksum mismatch incl. deleted applied file, lock not acquired, SQL error rolls back only the
    failing file, bad requests without connecting, log line without SQL or foreign messages) and
    `lambdas/shared/tests/test_db.py` (IAM token as password, TLS `CERT_REQUIRED` + host name check, port 5432, env
    names per spec 06, `DB_PASSWORD`/`DB_SECRET_ARN` ignored, every failure → `DB_CONNECT_FAILED`, no client or
    connection at import). **Verified.**
  - AC-06.1: file read against spec 06 §Outputs and checked by a static test (exact column list, no
    CHECK/UNIQUE/INDEX/REFERENCES/embedding). Local run against PostgreSQL 14 **not verified** — Docker engine not
    running on the agent's machine; the owner can run it: `docker compose up -d`, set
    `MIGRATE_TEST_DATABASE_URL=postgresql://app:app@localhost:5432/aws_challenge`, run pytest (python-lambda skill).
  - Packaging: `py -3.13 lambdas/package.py migrate` → `build/lambdas/migrate.zip`, 91 files (function, `db.py`,
    `migrations/V1__create_users.sql`, pg8000 + deps; no tests, no `.pyc`, no binaries); rebuild gives the same
    SHA-256 `1E95C231…490E`; the extracted zip imports in an isolated interpreter and a `status` invoke without env
    vars ends in `DB_CONNECT_FAILED` (errorClass `KeyError`) with one log line, no network call. **Verified.**
  - Secret check: no secret, password or connection string with credentials in `lambdas/` (search for
    `password|secret` finds only the IAM-token parameter and test sentinels).
  - Not verified (AWS side, T03-03): TLS trust of the RDS Proxy certificate by the Lambda runtime's default store,
    `execute_simple` against RDS Proxy, IAM auth end to end.
  Open points for the owner: `.gitignore` lacks `.venv/`, `__pycache__/`, `.pytest_cache/` (out of this task's scope,
  one-line proposal); the old Docker volume `pgdata` (PG 17) can be removed by the owner if no longer needed; agent
  front matter `skills:` may list `python-lambda` / `postgres-migrations` (owner/architect decision).
- ARCH review 2026-11-16: **pass**, no blocking findings. Checked against design user-sync §1/§2/§5, spec 06 and this
  task's constraints/scope. Re-run by ARCH (fresh Python 3.13.2 venv from the pinned files): pytest
  `lambdas/shared lambdas/migrate` 53 passed, 1 skipped; `package.py migrate` → 91 files, SHA-256
  `1e95c231…eb490e` (identical to the backend build); zip root holds only `lambda_function.py`, `db.py`,
  `migrations/V1__create_users.sql` + pinned deps. V1 matches spec 06 §Outputs column for column. AC-06.1 local run
  against PostgreSQL 14 still **not verified** (Docker engine not running). As-built fit: env vars have no defaults
  (spec 06) — T03-03 sets `DB_NAME=postgres`, `DB_USER=postgres`, `DB_PROXY_ENDPOINT` = proxy endpoint, role
  resource `dbuser:prx-019d0caac664f7be9/postgres` (ENVIRONMENT.md); `users` lands in database `postgres`, schema
  `public` (master user, R-16). Python 3.12: no 3.13-only construct, packaged deps need ≥ 3.11 — static check only
  (no 3.12 interpreter); the 3.13 runtime is set by T03-03 (new `migrate`), T03-05 (`sync`), T03-07 (`admin`).
  Non-blocking findings (follow-up task or fix before T03-04/T03-06 reuse the code):
  1. `lambdas/shared/db.py:19` + `lambdas/migrate/lambda_function.py:183` — the 10 s socket timeout applies to every
     read, so a later migration statement running > 10 s fails as a raw socket/InterfaceError, not
     `MIGRATION_FAILED`. Fix: `db.connect(timeout=55)` in migrate (function timeout 60 s).
  2. `lambdas/migrate/lambda_function.py:105-108` — only `DatabaseError` maps to `MIGRATION_FAILED`; an
     `InterfaceError` (connection lost mid-file) surfaces as a foreign message in the Test-tab result. Fix: map it to
     `MIGRATION_FAILED: V<n> UNKNOWN` or accept as is.
  3. `lambdas/package.py:83-84` — requirements are installed before the function files are copied; a function file
     named like an installed package overwrites it silently (only the `shared/` clash is checked). Fix: same clash
     check for the function tree.
  4. `.gitignore` — no `.venv/`, `__pycache__/`, `.pytest_cache/` although the python-lambda skill requires them out
     of Git (proposal, owner decision; caches from the ARCH run were removed).
  5. For the T03-03 runbook (not code): verify TLS trust of the proxy certificate on the first `status` invoke
     (skill fallback documented); recommend switching the proxy's *Require TLS* on together with IAM auth.
  Doc fix by ARCH: `sg-lambda` (does not exist as built) replaced by "Lambda security groups as built
  (ENVIRONMENT.md)" in spec 06 AC-06.4, T03-03 and design user-sync §2.
- 2026-11-16 (backend): ARCH findings 1–3 fixed; status stays `Review` (re-review by ARCH).
  1. `migrate/lambda_function.py`: `DB_TIMEOUT_S = 55.0`, handler calls `db.connect(timeout=DB_TIMEOUT_S)`; the
     shared default (10 s) is unchanged for the API functions.
  2. `_apply`: the whole per-file transaction (lock, re-check, file, history row, `COMMIT`) is guarded;
     `DatabaseError` → `MIGRATION_FAILED: V<n> <SQLSTATE>` (as before), `InterfaceError` or raw `OSError` (pg8000
     does not wrap the first socket read, so a timeout can surface as `TimeoutError`) →
     `MIGRATION_FAILED: V<n> UNKNOWN`, rollback attempted quietly. Spec 06 has no connection-loss code; this is the
     existing `MIGRATION_FAILED: V<n> <SQLSTATE>` form with the `UNKNOWN` placeholder the runner already used for an
     error without SQLSTATE — no new error code, spec unchanged. A loss during `COMMIT` leaves the outcome unknown;
     `status` shows it (skill postgres-migrations updated).
  3. `package.py`: after installing requirements, every included top-level entry of the function tree and every
     `shared/*.py` is checked against the staging root (`x.py` vs `x/` vs `x.py`); clash → `SystemExit("name clash in
     build/lambdas/<function>: <origin>/<name>")`, no zip written.
  Tests: `migrate/tests` +7 (lost connection in file / raw `TimeoutError` / history insert / `COMMIT`, failing
  rollback swallowed, handler log line without the foreign message, connect called with `timeout=55.0`); handler
  stubs of `db.connect` accept keyword args; new `lambdas/tests/test_package.py` (6: zip content without tests, four
  clash kinds, shared clash; pip stubbed, no network). Skills `python-lambda`, `postgres-migrations` and
  `lambdas/README.md` updated.
  Evidence (Python 3.13.2, scratch venv outside the repo): `pytest lambdas/shared lambdas/migrate` **60 passed,
  1 skipped** (optional integration test, env var not set); migrate alone 47 + 1 skipped, shared 13; `pytest
  lambdas/tests` 6 passed; all three together 66 + 1 skipped. `py lambdas/package.py migrate` → 91 files,
  430 982 bytes, SHA-256 `D5257298E8CF5F8416AF8A56204C202754EBA92CEEBCBCBD442B9883A0EE3A37` (base64
  `1SVymOjPX4QWr4pWIEwgJ1TrqSzuvLy9RCuYg6DuOjc=`), identical on rebuild; extracted zip imports, `DB_TIMEOUT_S`
  55.0, `status` without env vars → `DB_CONNECT_FAILED` (errorClass `KeyError`), one log line. T03-03 hash lines
  updated. Not verified: behaviour against a real PostgreSQL/RDS Proxy (Docker engine not running; AWS is T03-03).
- 2026-11-16 (ARCH, owner decisions): **re-opened → `Todo`.** No function `aws-challenge-migrate` (ADR-017 revised,
  Q-16 amended): the runner moves into `aws-challenge-sync`; runtime Python 3.12 (ADR-015 revised). The move is done
  here, not in T03-04, so T03-03 can run the first migration through `sync` without waiting for the upsert. The
  reviewed runner logic is kept as is; only location, entry point and dispatch change. Exact changes for backend:
  1. `git mv lambdas/migrate/lambda_function.py lambdas/sync/migrator.py`; rename `lambda_handler` to
     `handle(event, context)` (same body); docstring: "migration runner of aws-challenge-sync, reached through the
     dispatch in lambda_function.py". Unchanged: `MIGRATIONS_DIR` (still `Path(__file__).parent / "migrations"`),
     `FILE_NAME`, `LOCK_KEY`, `DB_TIMEOUT_S = 55.0`, every error string and the log line. Not `migrations.py` — it
     would clash with the `migrations/` directory in the packager.
  2. `git mv lambdas/migrate/migrations lambdas/sync/migrations` and `git mv lambdas/migrate/requirements.txt
     lambdas/sync/requirements.txt` — byte-identical (V1 checksum), pins unchanged.
  3. New `lambdas/sync/lambda_function.py` with `lambda_handler(event, context)`: `isinstance(event, dict)` and
     `"action" in event` → `return migrator.handle(event, context)`; every other event → one log line and function
     error `UNSUPPORTED_EVENT` (spec 06 §Outputs: `level` `ERROR`, `message` `UNSUPPORTED_EVENT`, `function`,
     `awsRequestId`, `outcome` `failure`, `durationMs`; never the event; no DB connection). Leave an obvious place for
     T03-04's `UserConfirmed` branch (checked after `action`, before the fallback). Delete `lambdas/sync/.gitkeep`.
  4. Tests: move `lambdas/migrate/tests/*` to `lambdas/sync/tests/`; `test_migrate.py` → `test_migrator.py`,
     `test_migrate_integration.py` → `test_migrator_integration.py`; `import lambda_function as lf` → `import migrator
     as lf` in them and in `fake_db.py`; handler tests call `migrator.handle` and `Context.function_name =
     "aws-challenge-sync"`; `MIGRATE_TEST_DATABASE_URL` keeps its name. New `tests/test_dispatch.py`: `{"action":
     "status"}` reaches `migrator.handle`; `{"action":"x"}` → `MIGRATION_BAD_REQUEST`; `{}`, the console default
     template `{"key1":"value1","key2":"value2","key3":"value3"}`, a `UserConfirmed` envelope and a non-dict →
     `UNSUPPORTED_EVENT`, `db.connect` not called, exactly one log line with the fields above.
  5. Delete the empty `lambdas/migrate/` and the stale `build/lambdas/migrate*` (build output, git-ignored).
  6. `lambdas/package.py` `_install_requirements`: add `"--python-version", "3.12"` to the pip call (allowed with
     `--target` + `--only-binary=:all:`), so a pin without 3.12 support fails the build; one test in
     `lambdas/tests/test_package.py` asserting the flag. Usage text (`py -3.13`) unchanged — it is the build
     interpreter.
  7. `lambdas/requirements-dev.txt` comment: "boto3 of the Lambda Python 3.12 runtime". `lambdas/README.md`:
     "Python 3.12 runtime (local tests on 3.13)"; drop the `migrate/` row; `sync/` row: "copies Cognito users into
     PostgreSQL (T03-04) and applies the SQL migrations in `sync/migrations/` on the owner's invoke (ADR-017)".
  8. 3.12 check: no 3.13-only API in `lambdas/` (e.g. `copy.replace`, `warnings.deprecated`, `typing.ReadOnly`,
     `typing.TypeIs`, PEP 696 type-parameter defaults); state "static check only" in Notes.
  9. Evidence: `pytest lambdas/shared lambdas/sync`, `pytest lambdas/tests`; `py -3.13 lambdas/package.py sync` →
     file count, bytes, SHA-256 hex and base64 (Lambda's *Code SHA256* form), identical on rebuild; record here and in
     T03-03 Notes. Then status `Review` (ARCH re-review of the move).
- 2026-11-16 (backend, rework 1–9 done): status `Review` (ARCH re-review of the move; PLAN.md not edited by backend).
  1–2. The files under `lambdas/migrate/` were untracked (never committed), so `git mv` was not possible: moved with
     plain `mv`, content unchanged. `lambdas/sync/migrator.py`: only the docstring and `lambda_handler` → `handle`
     changed; `MIGRATIONS_DIR`, `FILE_NAME`, `LOCK_KEY`, `DB_TIMEOUT_S = 55.0`, error strings and the log line
     unchanged. `migrations/V1__create_users.sql` SHA-256 `9800e6e7…a9a5c7` and `requirements.txt` `fd976ede…fd5d45`
     identical before and after the move (byte-identical).
  3. New `lambdas/sync/lambda_function.py`: `isinstance(event, dict) and "action" in event` → `migrator.handle`;
     marked place for T03-04's `UserConfirmed` route; else one log line (`level` `ERROR`, `message`
     `UNSUPPORTED_EVENT`, `function`, `awsRequestId`, `outcome` `failure`, `durationMs`; no event content) and
     function error `UnsupportedEventError("UNSUPPORTED_EVENT")`; no DB connection. `lambdas/sync/.gitkeep` deleted.
  4. Tests moved to `lambdas/sync/tests/` (`test_migrator.py`, `test_migrator_integration.py`, `fake_db.py`,
     `conftest.py`), `import migrator as lf`, `lf.handle`, `function_name = "aws-challenge-sync"`;
     `MIGRATE_TEST_DATABASE_URL` unchanged. New `tests/test_dispatch.py` (9): `{"action":"status"}` reaches
     `migrator.handle`; `{"action":"x"}` → `MIGRATION_BAD_REQUEST`; `{}`, console default template, `UserConfirmed`
     envelope, `None`, `[]`, a string, a list → `UNSUPPORTED_EVENT`, `db.connect` and the runner not called, exactly
     one log line with exactly the spec fields, no event content.
  5. `lambdas/migrate/` and `build/lambdas/migrate`, `build/lambdas/migrate.zip` deleted.
  6. `package.py` pip call: `--python-version 3.12`; test `test_requirements_are_resolved_for_the_lambda_runtime_python_3_12`.
  7. `requirements-dev.txt` comment and `lambdas/README.md` (3.12 runtime, `migrate/` row dropped, `sync/` row) updated.
     Skills `python-lambda`, `postgres-migrations` checked against the code: consistent, no change needed.
  8. 3.12 check, **static check only**: search in `lambdas/**/*.py` for `copy.replace`, `warnings.deprecated`,
     `ReadOnly`, `TypeIs`, `NoDefault`, PEP 695/696 generic syntax and type-parameter defaults, `type` statements,
     `PythonFinalizationError`, `Path.from_uri`/`full_match`, `queue.ShutDown`, `os.process_cpu_count`,
     `base64.z85*` — no match. No 3.12 interpreter available; `package.py` now resolves wheels for 3.12 (build green).
  9. Evidence (Python 3.13.2, scratch venv in %TEMP% from the pinned files, removed afterwards):
     `pytest lambdas/shared lambdas/sync` **69 passed, 1 skipped** (optional integration test, env var not set);
     `lambdas/sync` alone 56 passed + 1 skipped; `pytest lambdas/tests` **7 passed**.
     `py -3.13 lambdas/package.py sync` → `build/lambdas/sync.zip`, **92 files, 431 888 bytes**, SHA-256 hex
     `08D77249F1170D315F3B05AD9C77D3A24E5E740CEBEB55FD5B9D9B4780C73DC4`, base64
     `CNdySfEXDTFfOwWtnHfTok5edAzr61X9W52bR4DHPcQ=`, identical on rebuild; zip root: `lambda_function.py`,
     `migrator.py`, `db.py`, `migrations/V1__create_users.sql` + pinned deps; no tests, no `.pyc`. Extracted zip in an
     isolated interpreter: `{}` → `UNSUPPORTED_EVENT` with the spec log line; `{"action":"status"}` without env vars →
     `DB_CONNECT_FAILED` (errorClass `KeyError`), `DB_TIMEOUT_S` 55.0. Hash recorded in T03-03 Notes.
     AC-06.2 **verified** (unit tests incl. dispatch). AC-06.1: static test green; local run against PostgreSQL 14
     **not verified** (Docker not run). Not verified: anything on AWS (T03-03).
- ARCH re-review 2026-11-16: **pass with one blocking finding (F1, owner decision on scope).** The move matches the
  ARCH change list 1–9, spec 06 §Inputs dispatch table / §Outputs (`UNSUPPORTED_EVENT` log line exactly
  `level`/`message`/`function`/`awsRequestId`/`outcome`/`durationMs`, no event content, no DB connection; `action`
  checked first, marked place for T03-04) and the skills `python-lambda` / `postgres-migrations`. `migrator.py` keeps
  `MIGRATIONS_DIR`, `FILE_NAME`, `LOCK_KEY`, `DB_TIMEOUT_S = 55.0`, error strings and log line; `package.py:63`
  passes `--python-version 3.12` (test `test_package.py:62`). Re-run by ARCH (fresh Python 3.13.2 venv in %TEMP% from
  the pinned files, removed afterwards; review caches removed): `pytest lambdas/shared lambdas/sync` **69 passed,
  1 skipped**; `pytest lambdas/tests` **7 passed**; `package.py sync` → 92 files, 431 888 bytes, SHA-256
  `08d77249…780c73dc4`, base64 `CNdySfEXDTFfOwWtnHfTok5edAzr61X9W52bR4DHPcQ=` — identical to T03-02/T03-03 Notes and on
  rebuild; zip root `db.py`, `lambda_function.py`, `migrator.py`, `migrations/V1__create_users.sql` + pinned deps, no
  tests/`.pyc`. V1 SHA-256 `9800e6e7…44fa9a5c7`, `requirements.txt` `fd976ede…d7fd5d45` = the values recorded by
  backend; all files under `lambdas/` are LF. AC-06.1 local run still **not verified**; 3.12: static check only.
  1. **Blocking (before the first commit of `lambdas/` and before the T03-03 upload/first `migrate`):** `core.autocrlf
     = true` and `.gitattributes` has no rule for `lambdas/`. Any later checkout on Windows turns `V1__create_users.sql`
     (and `.py`) into CRLF → different file SHA-256 → `MIGRATION_CHECKSUM_MISMATCH: V1` on every sync zip built after
     V1 was applied from the LF build, and the recorded zip hash is no longer reproducible. Fix (out of this task's
     scope → owner approval): add `lambdas/** text eol=lf` to `.gitattributes`; files are already LF, so the zip hash
     stays `08d77249…`.
  2. Non-blocking: `lambdas/shared/db.py:1` docstring still says "(admin, sync, migrate)" → "(admin, sync)".
  3. Non-blocking: `.claude/skills/postgres-migrations/SKILL.md:42-43` says a `UserConfirmed` envelope "goes to the
     upsert" — add "(from T03-04; until then `UNSUPPORTED_EVENT`)".
  4. Non-blocking, still open from the first review: `.gitignore` lacks `.venv/`, `__pycache__/`, `.pytest_cache/`
     (pytest runs leave `__pycache__` as untracked files under `lambdas/`).
- 2026-11-16: set to `Done` by the owner (after ARCH re-review; `.gitattributes` LF rule and `.gitignore` Python entries added).
