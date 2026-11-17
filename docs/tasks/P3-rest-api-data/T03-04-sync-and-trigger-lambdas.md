---
id: T03-04
title: "Post-confirmation trigger and Sync Lambda code (Python, pytest)"
phase: P3-rest-api-data
status: Done
agent: backend
skills: [postgres-pro, test-master]
depends_on: [T03-02]
blocked_by: []
design: ../../design/user-sync.md
spec: ../../specs/07-user-sync.md
acceptance: [AC-07.1, AC-07.2]
---
# T03-04 — Post-confirmation trigger and Sync Lambda code

## // BUSINESS CONTEXT

W3-G1, S2 (curriculum: "Sync chain Cognito → EventBridge → Lambda"): every user the owner confirms must appear in
PostgreSQL so the administrator can list it. The trigger must never make a confirmation fail (R-02); the sync must
survive dirty values from direct `SignUp` calls (R-11, Q-14 C).

## // TECHNICAL CONSTRAINTS

- Conventions of the `python-lambda` skill (T03-02); shared DB helper; no network call at init; runtime Python 3.12
  (ADR-015 revised 2026-11-16): no 3.13-only API.
- `lambdas/post-confirmation/`: only `boto3` (`events.put_events`, one entry), env `EVENT_BUS_NAME`; allow-listed
  attributes only; never raises; returns the Cognito event unchanged (spec 07 §Behaviour 2–3).
- `lambdas/sync/`: extend the dispatcher of T03-02 (`lambda_function.py`) with the `UserConfirmed` route of spec 06
  §Inputs (after the `action` check, before the `UNSUPPORTED_EVENT` fallback); the upsert in its own module or in
  `lambda_function.py`; `migrator.py`, `migrations/` (V1 byte-identical — its checksum is applied in RDS by T03-03)
  and the existing dispatch tests stay green and unchanged. Mapping and outcomes exactly spec 07 §Outputs; one
  parameterised upsert; DB errors raise; DB socket timeout = the shared 10 s default (the function timeout is 60 s
  for the migration path).
- Log lines per spec 07 — no attribute values.
- pytest with test doubles (stub EventBridge client, fake DB connection).

## // SCOPE

**Implement**
- Both handlers, `requirements.txt` where needed, `tests/` covering AC-07.1, AC-07.2; zips build
- Skill `user-sync` (event schema pointer to spec 07, trigger rules, sync rules, re-sync runbook outline, how to
  test locally); skills ownership rule
- Sample event JSON for the owner's EventBridge *Send events* test (in the skill, no real personal data)

**Exclude**
- AWS changes (T03-05); `admin` handler (T03-06); embeddings (Week 4)

**Interfaces that must match**
- Event `source`, `detail-type`, detail fields: spec 07 §Inputs; table columns: spec 06.

## Definition of Done

- [ ] pytest green (AC-07.1, AC-07.2); zips build for both functions
- [ ] Skill `user-sync` added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-17 (wiring) and Q-18 (DB access).
- 2026-11-13: Q-17 A and Q-18 A accepted by the owner (ADR-016, ADR-006 revised); design user-sync `Accepted` →
  `Todo` (waits for T03-02 `Done`); scope unchanged.
- 2026-11-16 (ARCH, owner decisions): `sync` also hosts the migration runner (ADR-017 revised) — T03-02 creates
  `lambdas/sync/` with the dispatcher and the runner; this task adds the `UserConfirmed` branch to it. Runtime 3.12.
  `post-confirmation` stays (ADR-016, owner 2026-11-16).
- 2026-11-16 (backend): start gate checked — T03-02 `Done`, design user-sync `Accepted`, not blocked. Implemented:
  1. `lambdas/sync/user_sync.py` (new): `is_user_confirmed` (dispatch rule), validation (`sub` canonical UUID,
     `email` trimmed/lower-cased non-empty → else `rejected`, no DB call, no error), tolerant mapping per spec 07
     §Outputs (missing/empty → NULL silently; present but unusable → NULL + event field name in `invalidFields`; ASCII
     digits only; out-of-SPA-range integers stored when within PostgreSQL `integer`; `confirmedAt` without offset =
     UTC), one parameterised upsert `INSERT … ON CONFLICT (id) DO UPDATE … updated_at = now() RETURNING (xmax = 0)`
     (`created_at` untouched), `db.connect()` with the shared 10 s default, one log line. DB errors raise:
     `DB_CONNECT_FAILED` as is; pg8000 `DatabaseError`/`InterfaceError`/`OSError` → `UserSyncError` message
     `USER_SYNC_FAILED: <SQLSTATE|UNKNOWN>` (internal function error string, not in spec 07 — keeps foreign text
     with values out of the Lambda error; ARCH to confirm).
  2. `lambdas/sync/lambda_function.py`: route `UserConfirmed` → `user_sync.handle` after the `action` check, before
     the fallback (the marked slot). `migrator.py`, `migrations/V1__create_users.sql` and `requirements.txt`
     unchanged — SHA-256 `6f8ba316…537c1b68`, `9800e6e7…44fa9a5c7` (= T03-03 applied checksum, also inside the new
     zip), `fd976ede…d7fd5d45`.
  3. `lambdas/sync/tests/test_dispatch.py`: **one existing case changed (deviation from "unchanged")** — the
     parametrised `USER_CONFIRMED` case asserted `UNSUPPORTED_EVENT` ("no upsert route before T03-04"), which this
     task's route necessarily inverts; replaced by a test that the envelope reaches the upsert and never the runner,
     plus two near-miss envelopes (other `detail-type`, other `source`) that stay `UNSUPPORTED_EVENT`. All other
     dispatch and runner tests untouched. New `tests/test_user_sync.py` (AC-07.2) and optional
     `tests/test_user_sync_integration.py` (real upsert on local PostgreSQL 14, skipped without
     `MIGRATE_TEST_DATABASE_URL`).
  4. `lambdas/post-confirmation/` (new): `lambda_function.py` (boto3 only, no `requirements.txt`; env
     `EVENT_BUS_NAME` read in the handler; one `put_events` entry with the allow-listed detail; never raises;
     returns the same event object; `published` / `publish_failed` / `ignored`; EventBridge client lazy with
     connect/read timeout 1 s and `total_max_attempts` 2 so the worst case stays inside Cognito's 5 s), `tests/`
     (AC-07.1). Zip contains `shared/db.py` too (packager copies it into every zip; never imported by the trigger).
  5. `lambdas/shared/db.py:1` docstring "(admin, sync, migrate)" → "(admin, sync)".
  6. Skills: `user-sync` (new — trigger rules, sync rules, re-sync runbook outline with sample event detail
     (fictitious values), local tests); `python-lambda` layout (`user_sync.py`, `post-confirmation/`);
     `postgres-migrations` rule 0 (route now implemented). `lambdas/README.md` row for `post-confirmation/`.
- Evidence (Python 3.13.2, scratch venv in %TEMP% from the pinned files):
  - `pytest lambdas/shared lambdas/sync` **134 passed, 2 skipped** (both optional integration tests, env var not
    set); `pytest lambdas/post-confirmation` **13 passed**; `pytest lambdas/tests` **7 passed**.
  - `py -3.13 lambdas/package.py sync` → `build/lambdas/sync.zip`, **93 files, 434 967 bytes**, SHA-256 hex
    `B02EB57CCC46173D0A81C18D8AEEBD356B62E8A07A2D90A0094921490BC5F20B`, base64 (Lambda *Code SHA256*)
    `sC61fMxGFz0KgcGNiu69NWti6KB6LZCgCUkhSQvF8gs=`; identical on rebuild. Zip root: `db.py`, `lambda_function.py`,
    `migrator.py`, `user_sync.py`, `migrations/V1__create_users.sql` + pinned deps; no tests, no `.pyc`.
  - `py -3.13 lambdas/package.py post-confirmation` → `build/lambdas/post-confirmation.zip`, **2 files, 3 479
    bytes**, SHA-256 hex `856ACA1EDDC30D96FB190CA63B7CFEE2FB36A6CC02D2E281117BF053C207EA40`, base64
    `hWrKHt3DDZb7GQymO3z+4vs2pswC0uKBEXvwU8IH6kA=`; identical on rebuild. Zip: `lambda_function.py`, `db.py`.
  - Extracted zips in an isolated interpreter without AWS/DB env: sync — envelope with bad `sub` → `rejected` log
    line, valid envelope → `DB_CONNECT_FAILED` (`errorClass` `KeyError`); post-confirmation — ConfirmSignUp without
    region → `publish_failed` (`NoRegionError`), event returned (same object).
  - All `lambdas/**/*.py|*.sql` LF. 3.12 check: **static check only** (grep for the 3.13-only APIs listed in T03-02
    Notes — no match).
  - AC-07.1 **verified** locally; AC-07.2 **verified** locally (unit tests with doubles). **Not verified:** the
    upsert SQL against a real PostgreSQL 14 (Docker engine not running — run the integration test with
    `docker compose up -d` + `MIGRATE_TEST_DATABASE_URL`); everything on AWS (T03-05).
- 2026-11-16 (backend): status → `Review`. PLAN.md not edited (orchestrator).
- **ARCH review 2026-11-16: findings — 1 blocking, 3 non-blocking.** Reproduced in a scratch venv (Python 3.13,
  pinned files): `lambdas/shared lambdas/sync` 134 passed / 2 skipped, `lambdas/post-confirmation` 13 passed,
  `lambdas/tests` 7 passed; both zips rebuilt with the hashes above (identical); V1 SHA-256 = T03-03 applied checksum.
  Scope, dispatch order (spec 06 §Inputs), parameterised upsert, log fields (no values), never-raising trigger, lazy
  client, no init network call: as specified.
  Decisions on the backend's points:
  1. **Dispatch test change — accepted.** The old `USER_CONFIRMED → UNSUPPORTED_EVENT` case pinned the pre-T03-04
     state that this task's spec requires to change; the replacement (route reaches the upsert, never the runner) plus
     the `other-detail-type` / `other-source` near-misses keeps the negative coverage. Recorded as an accepted
     deviation from "unchanged"; all other dispatch/runner tests are untouched.
  2. **`USER_SYNC_FAILED: <SQLSTATE|UNKNOWN>` — accepted** (same pattern as `MIGRATION_FAILED: V<n> <SQLSTATE>` in
     spec 06; keeps driver text with values out of the function error). Added to spec 07 §Outputs ("Sync function
     errors", with `DB_CONNECT_FAILED`) and the §Edge Cases row "Proxy or DB unavailable"; no AC changed.
  3. **Trigger client timeouts — rejected as configured (blocking B1).** botocore standard mode: per attempt ≈
     connect 1 s + read 1 s; one retry with jitter backoff up to 1 s → worst case ≈ 2 + 1 + 2 = 5 s, plus cold-start
     init and DNS (not covered by the socket timeouts) — at or over both Cognito's 5 s wait and the 5 s function
     timeout, so a slow EventBridge could fail the owner's confirmation (R-02), contrary to the Notes/skill claim.
     A retry buys almost nothing here (learning volume, no throttling; `publish_failed` + re-sync covers a miss).
  - **B1 (blocking)** `lambdas/post-confirmation/lambda_function.py:35` → `Config(connect_timeout=1, read_timeout=2,
    retries={"total_max_attempts": 1, "mode": "standard"})` (worst case ≈ 3 s + init, inside 5 s); update the assert in
    `lambdas/post-confirmation/tests/test_post_confirmation.py:235-236` and the bullet in
    `.claude/skills/user-sync/SKILL.md:46-47` (state the ≈ 3 s worst case and "no retry; re-sync covers a miss"); fix
    item 4 of the backend Notes above accordingly; re-run pytest and rebuild the post-confirmation zip (new hashes).
  - N1 (non-blocking) Upsert SQL not run against real PostgreSQL 14 — run `test_user_sync_integration.py`
    (`docker compose up -d` + `MIGRATE_TEST_DATABASE_URL`) before T03-05 uploads the sync zip; else it stays "not
    verified" until AC-07.4.
  - N2 (non-blocking) `lambdas/sync/user_sync.py:134-136, :141-143, :151-153` name `confirmedAt`, `attributes` and non-string text
    attributes in `invalidFields`; spec 07 §Outputs only says so for `birthdate`/height/weight. Harmless superset (field
    names only); align the spec wording at the next spec 07 touch.
  - N3 (non-blocking) The post-confirmation zip carries an unused `db.py` (packager copies `shared/` everywhere);
    acceptable, documented in the skill.
  Re-review needed only for B1 (diff of the three files + new zip hash).
- 2026-11-16 (B1 fixed by the assistant): `lambdas/post-confirmation/lambda_function.py` client config now `connect_timeout=1, read_timeout=2, total_max_attempts=1`; test assert and the user-sync skill updated; `pytest lambdas/post-confirmation` 13 passed. New `post-confirmation.zip`: 2 files, 3 522 bytes, SHA-256 `0BDCBA9F97F61B0C9C61AB00A2BC8EFEAADBB797343A0D5450E5373B434F60F4` / base64 `C9y6n5f2GwycYasAoryO/qrbt5c0Og1UUOU3O0NPYPQ=` (replaces the earlier hash). `sync.zip` unchanged.
- 2026-11-17: set to `Done` by the owner (Week 3 closed).
