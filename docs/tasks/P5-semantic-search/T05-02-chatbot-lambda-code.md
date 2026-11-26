---
id: T05-02
title: "Chatbot Lambda: POST /chat (NL → SQL with guard / vector top-5), shared embeddings and HTTP helpers (Python, pytest)"
phase: P5-semantic-search
status: Review
agent: backend
skills: [python-lambda, admin-api, bedrock-embeddings, http-api-jwt, postgres-pro, test-master]
depends_on: []
blocked_by: []
design: ../../design/semantic-search.md
spec: ../../specs/12-chat-api.md
acceptance: [AC-12.1, AC-12.2, AC-12.3]
---
# T05-02 — Chatbot Lambda code

## // BUSINESS CONTEXT

Week 5 S2/S4 and the project requirement: an administrator asks a question in plain language; the Chatbot Lambda
returns rows — five similar users (vector) or statistics through LLM-generated SQL when the question contains "sql" —
and logs latency and tokens. The `chatbot` code exists only in the console today (R-15); from this task it lives in
Git and replaces the Week 1 placeholder.

## // TECHNICAL CONSTRAINTS

- Conventions of the `python-lambda` skill: Python 3.12 runtime (no 3.13-only API), `lambda_handler(event, context)`,
  clients created lazily, no network call or DB connection at init, parameterised SQL for every value, pytest with
  test doubles (no AWS, no DB).
- Contract exactly as spec 12: check order, body rules, mode rule, prefix regex, Converse request (model id constant,
  `inferenceConfig`, client connect 2 s / read 10 s / one attempt), prompt content, SQL guard rules and reject codes,
  `LIMIT` rewrite, executed text = guard rendering, `BEGIN READ ONLY` + `SET LOCAL statement_timeout = '4s'` +
  `ROLLBACK` around every query, DB socket timeout 5 s, row caps, response fields, value mapping, error mapping, one
  log line with exactly the listed fields and none of the forbidden values.
- SQL guard with `sqlglot` (PostgreSQL dialect) — the only new dependency: pure-Python wheel pinned in
  `lambdas/chatbot/requirements.txt` (no `sqlglot[rs]`, no Rust tokenizer); `package.py` must still pass its
  pure-Python check. Bedrock through `boto3` of the runtime (`converse` exists in every Python 3.12 runtime build —
  state the check in Notes).
- No duplication (CLAUDE.md §7): move `lambdas/sync/embeddings.py` → `lambdas/shared/embeddings.py` (adds
  `embed_with_usage(text) -> (vector, inputTokens)`; `embed()` unchanged) and the claims / `token_use` / `exp` checks,
  `parse_groups` and the problem+json / JSON response helpers from `lambdas/admin/lambda_function.py` →
  `lambdas/shared/http_api.py`; `bedrock_stub.py` → `lambdas/shared/tests/`. `admin` and `sync` behaviour and their
  existing tests unchanged (only imports / conftest paths change).
- No change to migrations, `sync` dispatch, `post-confirmation` or any spec 06–11 contract (Q-23 A: no `V3`
  migration, no extra DB role).

## // SCOPE

**Implement**
- `lambdas/chatbot/`: `lambda_function.py` (handler, routing, body, mode, response, log), `llm.py` (prompt, Converse
  call, error classes), `sql_guard.py`, `search.py` (vector query, row mapping), `requirements.txt`, `tests/`
  (AC-12.1, AC-12.2 incl. every hostile statement of spec 12 §Edge Cases)
- `lambdas/shared/embeddings.py`, `lambdas/shared/http_api.py`, `lambdas/shared/tests/bedrock_stub.py`; imports in
  `admin` and `sync` and their conftests; `lambdas/tests` if the packager test needs the new module list
- Zip builds `chatbot`, `sync`, `admin` with SHA-256 (hex + base64) in Notes (AC-12.3)
- Skills: new `chatbot-api` (handler, modes, prompt, guard, log line, tests, how to change the allowlists); updates
  `bedrock-embeddings` (shared module, `embed_with_usage`, chatbot use), `python-lambda` (layout, shared modules),
  `admin-api` (helpers moved); `lambdas/README.md` chatbot row; agent `backend` skills list gets `chatbot-api` and
  `bedrock-embeddings` (proposal to the owner, `.claude/agents` edit only with approval)

**Exclude**
- AWS changes and uploads (T05-01, T05-03); SPA (T05-04); DB roles / migrations (Q-23 A); Bedrock Agent; Powertools
  (Week 6)

**Interfaces that must match**
- Request/response/errors: spec 12 (the SPA of T05-04 builds against it); model id: T05-01 evidence; env names:
  shared `db.py`; vector query and text template: spec 10/11 (`embed_with_usage` produces the same vector as `embed`).

## Definition of Done

- [x] `pytest` green for `lambdas/shared`, `lambdas/chatbot`, `lambdas/sync`, `lambdas/admin`,
  `lambdas/post-confirmation`, `lambdas/tests` (counts in Notes); three zips build; 3.12 check stated
- [ ] Skills added/updated; ARCH review passed (SQL guard reviewed line by line)
- [ ] Status updated here (`Review`) and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-25: created by Week 5 planning; `Blocked` by Q-21 (direct Converse vs agent changes the code shape), Q-22
  (model id, request format) and Q-23 (DB privileges; option B adds a migration).
- 2026-11-25: owner answered Q-21 A, Q-22 (Nova Micro, `eu.amazon.nova-micro-v1:0`), Q-23 A (R-19 accepted); design
  semantic-search `Accepted` → `Todo`, startable. Agent `backend` skills: `bedrock-embeddings` proposed now (skill
  exists); `chatbot-api` is added to the agent once this task has created the skill (owner edit of
  `.claude/agents/backend.md`).
- 2026-11-25 (backend): implemented; status `Review` (PLAN.md row left to the coordinator, as instructed).
  - **Code:** `lambdas/chatbot/` `lambda_function.py`, `llm.py`, `sql_guard.py`, `search.py`, `requirements.txt`,
    `tests/` (`conftest.py`, `doubles.py`, `test_sql_guard.py`, `test_llm.py`, `test_search.py`,
    `test_chatbot_api.py`, optional `test_chatbot_integration.py`); `.gitkeep` removed. Moved:
    `lambdas/sync/embeddings.py` → `lambdas/shared/embeddings.py` (+ `embed_with_usage`, `error_class` made public;
    `embed` = `embed_with_usage(text)[0]`, same request/vector/errors), `sync/tests/bedrock_stub.py` and
    `sync/tests/test_embeddings.py` → `lambdas/shared/tests/`; HTTP helpers → `lambdas/shared/http_api.py` (adds
    `is_admin`, titles 429/502). `admin/lambda_function.py` imports them (behaviour unchanged, `parse_groups` still
    importable); `sync/tests/conftest.py` adds `lambdas/shared/tests` to `sys.path`. No change to migrations, sync
    dispatch, `post-confirmation`, `package.py` or `lambdas/tests` (packager test needs no module list).
  - **Dependency:** `sqlglot==30.35.0` — wheel `sqlglot-30.35.0-py3-none-any.whl`, `Requires-Python >=3.9`, no
    required dependencies (extras `c`/`rs` = `sqlglotc`/`sqlglotrs` not installed); `package.py` pure-Python check
    passed (no `.pyd/.so` in the zip). Guard arg keys `from_`/`with_` are those of sqlglot 30.x (pinned).
  - **Design detail beyond the spec wording (stricter, for the ARCH review):** the guard is an allowlist of sqlglot
    node classes compared with `type(node) is X`; a table alias with a column list (`users u(a, b)`) is
    `TABLE_NOT_ALLOWED` (could rename `embedding`); the select-list alias exception never applies to `embedding` or
    system columns (GROUP BY/HAVING resolve input columns first); the guarded statement is executed with
    `execute_unnamed` (extended protocol: PostgreSQL itself refuses a second statement); the `sqlglot` logger is
    disabled (its warnings quote SQL). Reject codes for spec hostile cases chosen as: `SELECT set_config(…)`,
    `SELECT pg_sleep(10)`, `SELECT current_user`, `::regclass` → `FUNCTION_NOT_ALLOWED`; `pg_shadow`, derived table,
    `JOIN pg_user` → `TABLE_NOT_ALLOWED`; `*`/`embedding` → `COLUMN_NOT_ALLOWED`; `WITH`, `UNION`, `FOR UPDATE`,
    `INTO`, `DELETE`, `DROP` → `NOT_SELECT`; `SELECT 1; DELETE …` → `MULTIPLE_STATEMENTS`. 400 details not fixed by
    the spec: `body must be at most 4096 bytes`, `query parameters are not accepted`, `query must name what the users
    are similar to` (empty after the prefix); missing `query` uses `query must be 1 to 500 characters`. Log
    `message` on 502 = `BEDROCK_FAILED`. Interval values are rendered in PostgreSQL `postgres` IntervalStyle from
    pg8000's value (pg8000 merges a day/time mix into one `timedelta`, so the text can differ in form, not in value).
  - **pytest** (temp venv outside the repo, `py -3.13`, `lambdas/requirements-dev.txt` + `lambdas/chatbot/requirements.txt`;
    one session per directory): `lambdas/shared` 78 passed (HEAD: 13); `lambdas/chatbot` 271 passed, 22 skipped
    (integration, no DB); `lambdas/sync` 187 passed, 3 skipped (HEAD: 225 + 3 — the 38 `test_embeddings.py` tests moved
    with the module to `lambdas/shared`; shared + sync 238 → 265); `lambdas/admin` 91 passed, 6 skipped (= HEAD);
    `lambdas/post-confirmation` 13 passed (= HEAD); `lambdas/tests` 7 passed (= HEAD). AC-12.1, AC-12.2 covered by
    `test_chatbot_api.py`, `test_search.py`, `test_llm.py`, `test_sql_guard.py` (all 16 hostile statements of spec 12
    §Edge Cases with their code, 53 further hostile/unusable answers, the 5 required accepted forms + 14 more, every
    allowlisted function, LIMIT none/500/101/100/10/0/ALL/expression, comment and second statement never executed).
  - **Not verified:** `test_chatbot_integration.py` (guard renderings on PostgreSQL 14, `25006` on a write, vector
    order) — Docker Desktop was not running; run with `docker compose up -d` and `MIGRATE_TEST_DATABASE_URL`.
    Everything on AWS (AC-12.4 … AC-12.12) belongs to T05-01/T05-03/T05-05.
  - **3.12 check (static only):** no 3.13-only API used (only 3.10+ syntax: `X | Y` unions, dataclasses, `re`,
    `hashlib`, `base64`, `decimal`); all pins have `py3-none-any` wheels for 3.12 (`package.py --python-version 3.12`
    resolved them). `Converse` exists in boto3/botocore since 1.34.116 (May 2024); the Lambda Python 3.12 runtime
    ships a newer boto3 — not verifiable here, first proof is the T05-03 SQL-mode call (a missing method would show
    as 502 `errorClass` `AttributeError`). Local import of the extracted chatbot zip incl. boto3: ≈ 0.36 s.
  - **Zips** (`py -3.13 lambdas/package.py <fn>` → `build/lambdas/`; the extracted chatbot zip was imported and invoked
    once in isolation → 403 as expected):

    | Zip | Files | Bytes | SHA-256 (hex) | SHA-256 (base64) |
    |---|---|---|---|---|
    | `chatbot.zip` | 288 | 1292198 | `2541ad871e0722a721f0ee780bddc56b9e1f29f9dff5597584359a2bfda1cb15` | `JUGthx4HIqch8O54C93Fa54fKfnf9Vl1hDWaK/2hyxU=` |
    | `sync.zip` | 97 | 445612 | `380e945231284868b595c8d6c947322852a07b1833a23b291ea8693a2578de9c` | `OA6UUjEoSGi1lcjWyUcyKFKgexgzojspHqhpOiV43pw=` |
    | `admin.zip` | 92 | 435600 | `e1cce2b4f34b266d3060a0c070f7eb84eeac9dfae40ad2a6d26ffa76612c4841` | `4czitPNLJm0wYKDAcPfrhO6snfrkCtKm0m/6dmEsSEE=` |

    `sync.zip` and `admin.zip` **change** (design §9): a build of HEAD gives sync 96 files / `03ab9a34…cd676`, admin
    90 files / `182bcc71…ac560`; the new sync zip adds `http_api.py` and a changed `embeddings.py`, the admin zip adds
    `embeddings.py` and `http_api.py` (+ the new admin handler). Both are re-uploaded in T05-03. The
    `post-confirmation` zip would also gain the two unused modules; not re-uploaded (design §9).
  - **Skills:** new `.claude/skills/chatbot-api/SKILL.md`; updated `bedrock-embeddings`, `python-lambda`, `admin-api`;
    `lambdas/README.md` chatbot and shared rows. **Proposal to the owner (not done, `.claude/agents` edit needs
    approval):** add `chatbot-api` to `skills:` of `.claude/agents/backend.md` (`bedrock-embeddings` is already there).
- ARCH review 2026-11-26: **findings — 1 blocking, 4 non-blocking**; back to `backend`, status stays `Review`.
  - **Re-run (temp venv `py -3.13`, outside the repo):** pytest shared 78, chatbot 271 + 22 skipped, sync 187 + 3,
    admin 91 + 6, post-confirmation 13, tests 7 — all equal the counts above. `package.py` rebuilt the three zips
    byte-identically: chatbot `2541ad87…cb15` (288 files), sync `380e9452…de9c` (97), admin `e1cce2b4…4841` (92).
  - **Confirmed:** the check order 401 → 404 → 403 → 400 comes before any Bedrock or DB call. The error mapping is
    429/502/400/500 with fixed details. The log line has only the listed fields (`sqlglot` uses only the logger
    `sqlglot`, which is disabled). Converse gets the model id, `inferenceConfig` and client 2 s / 10 s / 1 attempt
    (tested); the text blocks and usage are parsed defensively. The time budget stays under 29 s. `READ ONLY` +
    `SET LOCAL statement_timeout` + `ROLLBACK` wrap every query, and the guarded SQL runs through `execute_unnamed`
    (Parse message, no `:name` substitution). `embeddings.py` differs from HEAD only by `error_class` being public and
    `embed_with_usage`, so `embed()` keeps its request, vector and errors. `admin` differs only by the helper imports.
    The guard rejected all of the following: `(u).embedding`, `SELECT u`, `CAST(u AS text)` in the select list,
    `pg_catalog.*()`, dollar and `U&` strings, `FETCH FIRST`, `ROLLUP`, `ANY(ARRAY…)`, `xmin` and `xmin` used as an
    alias. Comments and a second statement never reach the rendered SQL.
  - **B1 (blocking) — the guard lets SQL read `embedding` through a whole-row reference, via the alias exception.**
    `lambdas/chatbot/sql_guard.py:256-263` with `_in_alias_clause` `:227-236` accepts any column anywhere *inside*
    `ORDER BY`/`GROUP BY`/`HAVING` if its name equals a select-list alias, even when that name is also the table name
    or a table alias. PostgreSQL resolves an output alias only when the whole `ORDER BY`/`GROUP BY` item is the bare
    name, and never in `HAVING`. Inside an expression, `u`/`users` is a **whole-row reference** that includes
    `embedding`. These statements were accepted (probe):
    `SELECT id, count(*) AS u FROM users u GROUP BY id HAVING max(CAST(u AS text)) LIKE '%[0.0%'`,
    `SELECT id, count(*) AS users FROM users GROUP BY id HAVING max(CAST(users AS text)) LIKE '%'`,
    `SELECT id AS u FROM users u ORDER BY length(CAST(u AS text)) DESC`. Together they give a per-user blind oracle
    over the vector, which violates spec 12 §SQL guard (rule text "a **bare name** in ORDER BY, GROUP BY or HAVING")
    and design §5. Impact: confidentiality only, admins only, and the vector is derived from allowed columns. The
    integrity layers are unaffected. PostgreSQL execution was **not verified** (Docker not running); the risk follows
    from PostgreSQL's name resolution rules.
    Fix:
    (a) apply the exception only when the Column is itself the item: `Ordered.this` of the select's `Order`, or a
        direct element of the select's `Group` expressions;
    (b) never apply it to a name in `_table_aliases(tree)`;
    (c) add the three probes above to `test_sql_guard.py` as `COLUMN_NOT_ALLOWED`, and update the
        `chatbot-api` skill line 74-75 to match.
    A `HAVING n > 1` alias stays harmless (PostgreSQL error → 400).
  - **N1:** `llm.py:110-118` ignores `stopReason`. A `max_tokens` cut ends as `PARSE_ERROR` 400, which is safe. Optional:
    treat it as `NO_QUERY`/`PARSE_ERROR` explicitly.
  - **N2:** `test_chatbot_integration.py` (renderings on PostgreSQL 14, `25006`, vector order) has still not run. Run
    it after the B1 fix, with Docker running.
  - **N3:** whether `converse` exists in the runtime boto3 is still unchecked locally. The first SQL call in T05-03 is
    the proof (as stated above).
  - **N4:** `SELECT …;;` (several trailing semicolons) is accepted as one statement. That is harmless because the
    rendering is executed, but it is looser than the spec ("a single trailing `;`"). Optional: reject it.
  - After the B1 fix: re-run pytest and the packager. The chatbot hash will change; record the new hash. The sync and
    admin zips must stay `380e9452…`/`e1cce2b4…`.
- 2026-11-26 (backend): ARCH review findings fixed; status stays `Review` for the re-review.
  - **B1 fixed** (`sql_guard.py`): `_in_alias_clause` replaced by `_is_alias_item`. The select-list alias exception now
    applies only when the column **is** a whole `ORDER BY` item (`Ordered.this` of the Select's `Order`) or a direct
    element of the Select's `GROUP BY`. It never applies inside an expression, never in `HAVING`, and never to a name
    that is the table name or a table alias (`_table_aliases`), in addition to `NEVER_ALIASES`. Tests
    (`test_sql_guard.py`): the three review probes plus 7 neighbours (`ORDER BY u`, `GROUP BY users`, `HAVING n > 1`,
    `ORDER BY n + 1`, `ORDER BY -n`, `GROUP BY h + 1`, alias used in a subquery's `ORDER BY`) → `COLUMN_NOT_ALLOWED`;
    3 bare-item cases still accepted (`ORDER BY n DESC NULLS LAST`, `GROUP BY band ORDER BY band`, `GROUP BY c`).
    Consequence: `HAVING <alias>` is now a guard rejection (400) instead of a PostgreSQL error (400); same status.
  - **N4 fixed:** more than one trailing `;` (`;;`, `; ;`) → `MULTIPLE_STATEMENTS` (sqlglot yields an empty entry);
    one trailing `;` is still allowed. 2 tests.
  - N1 (`stopReason`), N2 (integration test, Docker), N3 (runtime `converse`): unchanged, as stated in the review.
  - Skill `chatbot-api` §SQL guard updated (alias exception, `;;`).
  - **pytest** (temp venv outside the repo, `py -3.13`): shared 78; chatbot 286 passed, 22 skipped (was 271 + 22;
    +15 guard tests); sync 187 + 3 skipped; admin 91 + 6 skipped; post-confirmation 13; tests 7 — all green.
  - **Zips** (`py -3.13 lambdas/package.py …`): `chatbot.zip` 288 files, 1292436 bytes, SHA-256
    `9b5872510faea45dc0432f5c2877207bf68c4546ed194c254098edebcc87cc89` / base64
    `m1hyUQ+upF3AQy9cKHcge/aMRUbtGUwlQJjt68yHzIk=` (replaces `2541ad87…cb15` above). Unchanged, confirmed:
    `sync.zip` 97 files `380e945231284868b595c8d6c947322852a07b1833a23b291ea8693a2578de9c`, `admin.zip` 92 files
    `e1cce2b4f34b266d3060a0c070f7eb84eeac9dfae40ad2a6d26ffa76612c4841`. T05-03 runbook step table: chatbot hash
    row updated (hash lines only).
- ARCH re-review 2026-11-26: **pass** (B1, N4 closed; no blocking finding). The owner sets `Done`.
  - **Probes:** 30 hostile statements were all rejected:
    - the three B1 statements;
    - whole-row references through the table name or an alias, as a bare item or inside expressions in
      `ORDER BY`/`GROUP BY`/`HAVING`/`WHERE`/the select list;
    - `::text`/`CAST … AS varchar` of the row, `row_to_json`/`to_json`, `ROW(u.*)`, `(u.*)::text`;
    - a quoted or case-folded alias equal to a table alias, and an alias of a subquery table;
    - `HAVING n`, `ORDER BY n + 1`, `;;` and `; ;`.
  - **Still accepted (legitimate):** ordering by a select-list alias (`ORDER BY n DESC [NULLS LAST]`), grouping by an
    alias (`GROUP BY m`/`band`), `ORDER BY w`, qualified `u.col`, a single trailing `;`, and the AC-12.2 statistics
    query.
  - **Re-run:** pytest `lambdas/chatbot` 286 passed, 22 skipped. The rebuilt zips match the hashes above: chatbot
    `9b587251…cc89`, sync `380e9452…de9c`, admin `e1cce2b4…4841`.
  - **Non-blocking:**
    - `sql_guard.py:238` holds a run of spaces inside one physical line (looks like a lost line break; valid Python).
      Reformat when the file is next touched.
    - N1–N3 stay as recorded.
    - Not verified on PostgreSQL (Docker off; N2).
